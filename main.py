import libs
import os
from dotenv import load_dotenv
import psycopg2
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome import service as fs

def driver_init() -> webdriver.Chrome:
  '''
    Webブラウザを操作するためのWebDriveの設定を行う

    Returns:
      webdriver.Chrome: 設定をしたdriverを返す
    
    Note:
      CHROMEDRIVER: ローカルでchromedriverを使用する場合に使用
      CHROME_DRIVER_PATH: herokuでchromedriverを使用する場合のパス
  '''
  #CHROMEDRIVER = '/opt/chrome/chromedriver'
  CHROME_DRIVER_PATH = '/app/.chromedriver/bin/chromedriver'  #heroku driver path
  options = Options()
  options.add_argument('--headless')  
  options.add_argument('--no-sandbox')
  options.add_argument('--disable-dev-shm-usage')

  chrome_service = fs.Service(executable_path=CHROME_DRIVER_PATH)

  return webdriver.Chrome(service=chrome_service, options=options)

def main():
  '''
    学務情報システムから成績を読み込み、DBに存在しない場合はツイートして登録する

    Note:
      envファイルの設定が必要
  '''
  driver = driver_init()

  # time out 10s
  wait = WebDriverWait(driver,10)

  load_dotenv()
  user_id = os.getenv("GAKUJO_USERID")
  user_password = os.getenv("GAKUJO_PASSWORD")
  libs.login_gakujo(driver,wait,user_id,user_password)
  libs.move_kyoum_page(driver,wait)
  libs.move_performance_page(driver,wait)

  table_name = "perfomance"

  DATABASE_URL = os.environ.get('DATABASE_URL')
  conn = psycopg2.connect(DATABASE_URL)
  cursor = conn.cursor()

  if not libs.is_exists_table(cursor,table_name):
    libs.create_performance_db(driver,wait,conn,cursor,table_name)
  
  new_performance = libs.search_new_performance(driver,wait,cursor,table_name)

  if len(new_performance) != 0:

    libs.execute_tweet(os.getenv("TWITTER_API_KEY"),
                      os.getenv("TWITTER_API_KEY_SECRET"),
                      os.getenv("TWITTER_BEARER_TOKEN"),
                      os.getenv("TWITTER_ACCESS_TOKEN"),
                      os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
                      new_performance)

    if os.getenv("SLACK_WEBHOO_URL") != None:
      libs.execute_slack(os.getenv("SLACK_WEBHOO_URL"),new_performance)

    libs.insert_performance_db(conn,cursor,new_performance,table_name)

  cursor.close()
  conn.close()
  driver.quit()

if __name__ == "__main__":
  main()