#! /usr/bin/env python
# -*- coding: utf-8 -*-

import BackgroundNewsApi as api
import datetime
import os.path
import Queue
from threading import Thread
import time
import wx


IMAGE_DIR = "images"
WAVE_DIR = "articles"
RSS_URLS = ["https://news.google.com/news/feeds?ned=us&ie=UTF-8&oe=UTF-8&q&output=rss&num=3&hl=ja",
           ]

class Sub(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent=parent, title=title)

class Main(wx.Frame):
    playingArticle = None  # type:Article
    stoppedArticle = None  # type:Article
    flag_accept_play = False  # True when play button is pressed
    api = api.BackgroundNewsApi()  # type:api.BackgroundNewsApi
    __generator_article = None
    iv_routine_rss = 60 * 60  # 1h
    iv_routine_play = 3  # 3s

    def __init__(self, title):
        """
        img: image
        iv: interval time
        """
        img_play_file = "play.png"
        img_stop_file = "stop.png"

        # GUI
        wx.Frame.__init__(self, None, title=title, style=wx.MINIMIZE_BOX|wx.SYSTEM_MENU|wx.CAPTION|wx.CLOSE_BOX|wx.CLIP_CHILDREN)
        id_routine_rss = wx.NewId()

        # wigets
        self.st_title = wx.StaticText(self, label=u"ここに記事のタイトル\nが入ります")
        self.st_articleNum = wx.StaticText(self, label=u"ここに記事の総数が表示されます")
        self.st_lastModified = wx.StaticText(self, label=u" 更新")
        img_play = wx.Image(os.path.join(IMAGE_DIR, img_play_file), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn_play = wx.BitmapButton(self, bitmap=img_play)
        img_stop = wx.Image(os.path.join(IMAGE_DIR, img_stop_file,), wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn_stop = wx.BitmapButton(self, bitmap=img_stop)
        statusbar = wx.StatusBar(self)

        # timer
        tm_routine_rss = wx.Timer(self, id_routine_rss)

        # bind
        self.Bind(wx.EVT_BUTTON, self.OnPlayButton, btn_play)
        self.Bind(wx.EVT_BUTTON, self.OnStopButton, btn_stop)
        self.Bind(wx.EVT_TIMER, self.routineRss, tm_routine_rss)

        # layout
        self.SetStatusBar(statusbar)
        sr_main = wx.BoxSizer(wx.HORIZONTAL)
        sr_right = wx.BoxSizer(wx.VERTICAL)
        sr_left = wx.BoxSizer(wx.VERTICAL)
        sr_button = wx.BoxSizer(wx.HORIZONTAL)
        sr_button.Add(btn_play, 0)
        sr_button.Add(btn_stop, 0)
        sr_left.Add(sr_button, 1, flag=wx.EXPAND)
        sr_left.Add(self.st_lastModified, 0)
        sr_right.Add(self.st_title, 1, flag=wx.EXPAND)
        sr_right.Add(self.st_articleNum, 0)
        sr_main.Add(sr_left, 0)
        sr_main.Add(sr_right, 1, flag=wx.EXPAND)
        self.SetSizerAndFit(sr_main)

        # others
        self.SetStatusText(u"さて、次のニュースです")
        th = Thread(target=self.routine, kwargs={"evt":None})
        th.daemon = True
        th.start()
        tm_routine_rss.Start(self.iv_routine_rss)

    def routine(self, evt):
        """
        """
        if self.__generator_article == None:
            self.__generator_article = self.routineRss()
        while True:
            try:
                article = self.__generator_article.next()
                while True:
                    fname = os.path.join(WAVE_DIR, datetime.datetime.now().strftime(u"%Y%m%d%H%M%S_")
                                     #+ article.title[:5]
                                    ) + ".wav"
                    if os.path.exists(fname):
                        time.sleep(0.1)
                        continue
                    else: break
                self.translate(article, fname)
            except StopIteration:
                time.sleep(1)

    def routineRss(self):
        """
        get articles from rss
        """
        self.setPubDate(datetime.datetime.now())
        for url in RSS_URLS:
            for article in self.api.parse(url):
                print "rssroutine"
                yield article

    def translate(self, article, fname):
        """
        """
        print "routine Translate"
        if self.api.translate(article.description[:30], fname) == 0:
            article.wav = fname
            self.api.pushPlayQueue(article)
            return True
        else:
            print "translate failed"
            return False

    def checkStreamState(self, require):
        """
        require: [state]
        resturn
         - true : all require is include
        """
        res = True
        states = self.api.getStreamState()
        for i in require:
            res = res and (i in states)
        return res

    def routinePlay(self):
        u = self.api.stream_UNKNOWN
        w = self.api.stream_WAIT
        p = self.api.stream_PLAYING
        f = self.api.stream_FINISHED
        s = self.api.stream_STOPPED

        while self.flag_accept_play:

            print "================================================="
            print "routine Play"
            print "flag_accept_play:", self.flag_accept_play
            print "streamState:", self.api.getStreamState()
            print "stoppedArticle:", self.stoppedArticle
            print "playingArticle:", self.playingArticle

            self.setArticleNum(self.api.getPlayQueueNum())

            if self.checkStreamState((f,)):
                print "waiting"
                self.playingArticle = None
                time.sleep(self.iv_routine_play)

            if self.checkStreamState((w, s)):
                print "stopped and wait"
                print "replay article because stop button was pressed"
                self.playingArticle = self.stoppedArticle
                self.stoppedArticle = None
                self.api.play(self.playingArticle.wav)
                self.setArticleTitle(self.playingArticle.title)
            elif self.checkStreamState((w,)):
                print "finished and wait"
                # play next article
                print "play next article"
                try:
                    self.playingArticle = self.api.playNext()
                    if self.playingArticle == None: continue
                    self.setArticleTitle(self.playingArticle.title)
                    self.setArticleNum(self.api.getPlayQueueNum())
                    print "atricle num is seted"
                except Queue.Empty:
                    #self.notify(0, "there are not next article")
                    print "Queue is empty"
                except api.StreamingException:
                    print "Stream is live"
                except IOError:
                    print "IOError"
                    #self.notify(1, "not found call next wav")
            elif self.checkStreamState((p,)):
                print "playing"
                time.sleep(0.1)

            time.sleep(0.1)

    def play_start(self):
        th = Thread(target=self.routinePlay)
        th.daemon = True
        th.start()

    def play_stop(self):
        if self.api.getStreamState():
            self.api.stop()
            self.stoppedArticle = self.playingArticle
            self.playingArticle = None

    def notify(self, mode, string):
        """
        int mode 0:info 1:error
        """
        string += u"." if mode == 0 else u"!!"
        self.SetStatusText(string)

    def OnPlayButton(self, evt):
        print "OnPlayButton"
        if self.flag_accept_play:
            pass
        else:
            self.flag_accept_play = True
            self.play_start()

    def OnStopButton(self, evt):
        print "OnStopButton"
        if self.flag_accept_play:
            self.flag_accept_play = False
            self.play_stop()

    def setArticleTitle(self, string):
        """
        str string
        """
        title = ""
        i = 0
        for s in string:
            title += s
            i += 1
            if i % 14 == 0:
                title += "\n"
        wx.CallAfter(self.st_title.SetLabel, title)

    def setArticleNum(self, num):
        """
        int num
        """
        wx.CallAfter(self.st_articleNum.SetLabel, u"%2d記事" % num)

    def setPubDate(self, date):
        wx.CallAfter(self.st_lastModified.SetLabel, date.strftime(u"%m/%d %H:%M") + u" 更新")


if __name__ == "__main__":
    app = wx.App(False)
    f = Main("Speech")
    f.Show()
    app.MainLoop()