根据 [SvnExploit](https://github.com/admintony/svnExploit)，修改了 `svn<1.7` 的部分，`svn>1,7` 可以使用 [dumpall](https://github.com/0xHJK/dumpall)。

# Guide

仅支持 Python3，安装依赖库

```
sudo pip3 install -r requirements.txt
```

查看帮助

```
python3 svnDump.py -h
```

利用SVN源代码泄露下载源代码

```
python3 svnDump.py -u http://127.0.0.1/.svn
```
