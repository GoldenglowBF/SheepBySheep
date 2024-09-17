from imaplib import Flags
from pdb import Restart

#由于游戏是逐步开发的,因此可能出现一些不规范的代码

import pygame
import random

from numpy.random import randint
from pygame.display import update

WIDTH,HEIGHT = 600,720 #游戏窗口宽高

LEVEL_COUNT = [0,36,61,77,86] #每一层累加的卡片数，供后面计算用

DIFFICULTY = [[36,45,1],[90,180,5],[108,240,5]] #游戏的难度参数，三者分别对应卡片总数，时间限制，总层数

DIFFICULTY_INDEX = 1 #游戏难度索引

CARD_SIZE = 60  #每个卡片的宽高均为60像素

ROW,COL = 6,6  #第一层每行，每列均为6个卡片

GAME_FPS = 60

pygame.mixer.init() #初始化背景音乐播放器

pygame.mixer.music.load(r"music\maintheme.mp3") #载入主题音乐

SCORE_FILE_PATH = 'score.txt' #用于存储分数的文件位置

screen = pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("羊了个羊")

#从文件载入分数
def loadscore(filepath):
    with open(filepath,'r') as file:
        scoreboard = []
        for line in file.readlines():
            score = line.strip()
            scoreboard.append(int(score))
    return scoreboard

#粒子效果类，用于胜利后的粒子效果
class Particle(pygame.sprite.Sprite):
    def __init__(self,posx,posy):
        super().__init__()
        self.vecy = 1 #初始Y轴速度
        self.vecx = randint(-2,2) #初始X轴速度
        randsize = randint(20,50) #初始大小随机
        self.image = pygame.transform.scale( pygame.image.load(r"images\spark.png"), (randsize,randsize))
        self.rect = self.image.get_rect(center=(posx, posy))
    def update(self):
        #物理效果模拟
        self.rect.center = (self.rect.center[0]+self.vecx,self.rect.center[1] + self.vecy)
        self.vecy += 0.2
        if self.rect.center[0] > 800:
            self.kill()

#动图类，用于标题LOGO
class AnimImage(pygame.sprite.Sprite):
    def __init__(self,target):
        super().__init__()
        self.rawimg = None #原始图片，包含各个帧的图片
        self.frame = 0 #目前帧数
        self.oldframe = -1 #上一帧数
        self.framewidth = 1 #帧宽
        self.frameheight = 1 #帧高
        self.start = 0 #起始帧
        self.last = 0 #结束帧
        self.columns = 1 #序列帧的行，列数
        self.lasttime = 0 #上次记录的时间
    def loadimg(self,filename,width,height,columns,lastframe,posx,posy):
        self.rawimg = pygame.image.load(f"images\{filename}.png")
        self.framewidth = width
        self.frameheight = height
        self.rect = posx,posy,width,height
        self.columns = columns
        rect = self.rawimg.get_rect()
        self.last = lastframe
    def update(self,current_time,rate = 60):
        #以时间为判断依据，不断调整原始图片的裁剪窗口
        if current_time > self.lasttime + rate:
            self.frame += 1
            if self.frame > self.last:
                self.frame = self.start
            self.lasttime = current_time
        if self.frame != self.oldframe:
            frame_x = (self.frame % self.columns) * self.framewidth
            frame_y = (self.frame // self.columns) * self.frameheight
            rect = (frame_x,frame_y,self.framewidth,self.frameheight)
            self.image = self.rawimg.subsurface(rect)
            self.oldframe = self.frame

#按钮类，用于游戏交互
class Button(pygame.sprite.Sprite):
    def __init__(self,eventtype,text,posx,posy,width,height,textx,texty):
        super().__init__()
        self.type = eventtype #按钮的事件类型
        self.image = pygame.Surface((width,height)) #按钮的宽高
        self.image.fill((255,255,255)) #按钮的颜色
        self.rect = self.image.get_rect(center = (posx,posy)) #按钮的位置
        self.width = width #鼠标未在按钮上时按钮的宽
        self.height = height #鼠标未在按钮上时按钮的高
        self.posx = posx
        self.posy = posy
        self.targetsize = (width,height)
        self.textx = textx #文字与按钮的相对位置
        self.texty = texty
        font = pygame.font.Font('fonts\msyh.ttc', 20)
        self.displaytext = font.render(f"{text}", True, (0, 0, 0), None)
    def doevent(self):
        #按钮触发事件
        if self.type == 1:
            pygame.quit()
            return 1
        else:
            return self.type
    def update(self,mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.targetsize = (self.width+60,self.height)
        else:
            self.targetsize = (self.width,self.height)
        current_size = self.image.get_size()
        if self.targetsize != current_size:
            #通过插值实现按钮大小与颜色的平滑变化
            diff_width = self.targetsize[0] - current_size[0]
            diff_height = self.targetsize[1] - current_size[1]
            if abs(diff_width) < 1 and abs(diff_height) < 1:
                self.image = pygame.Surface((self.width,self.height))
            newwidth = current_size[0] + diff_width * 0.3
            newheight = current_size[1] + diff_height * 0.3
            self.image =  pygame.transform.scale(self.image,(newwidth,newheight))
            self.image.fill((255*(1-(current_size[0]-self.width)/60), 255, 255*(1-(current_size[0]-self.width)/60)))
        screen.blit(self.displaytext,(self.posx - self.textx,self.posy - self.texty))

#卡片类，整个游戏的核心
class Card(pygame.sprite.Sprite):
    def __init__(self,imgtype,pos,level,row,col):
        super().__init__()
        self.level = level #卡片处在的层
        self.row = row #卡片处在的行
        self.col = col #卡片处在的列
        self.ticksound = pygame.mixer.Sound(r"sound\tick.wav") #鼠标经过时触发的声音
        self.type = imgtype #卡片的类型
        self.image = pygame.transform.scale( pygame.image.load(f"images\card_{imgtype}.png"),(CARD_SIZE,CARD_SIZE)) #用于渲染的卡片图像
        self.defimage = pygame.transform.scale(pygame.image.load(f"images\card_{imgtype}.png"), (CARD_SIZE, CARD_SIZE)) #鼠标未在卡片上的图像
        self.darkimage = pygame.transform.scale(pygame.image.load(f"images\carddark_{imgtype}.png"), (CARD_SIZE, CARD_SIZE)) #鼠标在卡片上的图像
        self.rect = self.image.get_rect(topleft = pos)
        self.originpos = pos #卡片初始位置
        self.targetpos = pos #卡片目标位置
        self.offset = 0 #卡片抖动的位移参数
        self.direction = 1 #卡片抖动的方向参数
        self.times = 4 #卡片抖动的次数参数
        self.randomdir = (randint(0,3),randint(0,3)) #卡片消除后的物理运动方向
        self.covered = False #卡片是否被遮盖
        self.selected = False #卡片是否被选中
        self.destroyed = False #卡片是否被消除
        self.soundplayed = False #鼠标经过卡片的音效是否播放
    def update(self, mouse_pos,tile):
        if self.destroyed:
            #卡片消除后执行物理效果，让画面更生动
            if self.rect.center[1] > 800:
                return
            self.rect.center = (self.rect.center[0] + self.randomdir[0],self.rect.center[1] + self.randomdir[1])
            self.randomdir = (self.randomdir[0],self.randomdir[1]+1)
            return
        if 5 > self.level > 0 and not self.selected and not self.destroyed:
            #卡片的遮盖计算
            for lrow in range(self.row, self.row + 2):
                for lcol in range(self.col, self.col + 2):
                    tile.sprites()[LEVEL_COUNT[self.level - 1] + lrow * (6 - self.level + 1) + lcol].covered = True
        elif self.level == 5 and not self.selected and not self.destroyed:
            # 第三难度下出现多层堆叠的卡片，采用特殊方法计算遮盖
                for j in range(self.col):
                    tile.sprites()[90 + self.row * 9 + j].covered = True
        if self.covered:
            #卡片被遮盖时采用更暗的图像，便于辨认
            self.image = self.darkimage
        else:
            self.image = self.defimage
        if self.selected:
            #选中后修改卡片的目标位置，通过插值来实现卡片的平滑移动
            if self.targetpos != self.rect.center:
                diff_x = self.targetpos[0] - self.rect.center[0]
                diff_y = self.targetpos[1] - self.rect.center[1]
                if abs(diff_x) < 1 and abs(diff_y) < 1:
                    self.rect.center = self.targetpos
                newx = self.rect.center[0] + (self.targetpos[0] - self.rect.center[0]) * 0.3
                newy = self.rect.center[1] + (self.targetpos[1] - self.rect.center[1]) * 0.3
                self.rect.center = (newx,newy)
            return
        edge = 2
        if self.rect.collidepoint(mouse_pos) and not self.covered:
            #鼠标经过后的抖动计算，由CHATGPT提供思路
            if not self.soundplayed:
                self.ticksound.play()
                self.soundplayed = True
            if self.times > 0:
                self.offset += self.direction
                if abs(self.offset) >= edge:
                    self.direction *= -1
                    self.times -= 1
                if self.times == 0:
                    self.offset = 0
        else:
            self.soundplayed = False
            self.times = 4
            self.offset = 0
            self.direction *= -1
        self.rect.topleft = (self.originpos[0] + self.offset,self.originpos[1])

def getcardtile(types,totalcount):
    #牌堆序列的创建，算法思路由CHATGPT提供并加以改进
    if  totalcount != 36:
        totalcount -= 9
    maxcount = totalcount // types
    remain = totalcount
    tile = []
    for i in range(types):
        countoftype = random.randint(1,maxcount//3) * 3
        tile.extend([i+1]*countoftype)
        remain -= countoftype
    #这种算法的计算得出的卡片堆中，最后一种的卡片数量会偏高，这样的好处是减少无解局的出现
    if remain > 15:
        for i in range((remain - 15) // 3):
            tile.extend([randint(1,11)] * 3)
        remain = 15
    tile.extend([types] * remain)
    random.shuffle(tile)
    #难度二与三中，我们要确保牌堆顶的卡片能够消除，否则会出现开局即死局的情况
    if totalcount == 81:
        for i in range(3):
            tile.extend([randint(1,12)] * 3)
    elif totalcount == 99:
        for i in range(3):
            ranint = randint(1,12)
            for j in range(3):
                tile.insert(81 + i * 3 + j,ranint)
    return tile

#根据牌堆来生成卡片
def draw_cards():
    cardtile = getcardtile(12,DIFFICULTY[DIFFICULTY_INDEX][0])
    cards = pygame.sprite.Group()
    for level in range(DIFFICULTY[DIFFICULTY_INDEX][2]):
        for row in range(ROW-level):
            for col in range(COL-level):
                if level > 0:
                    for lrow in range(row,row+2):
                        for lcol in range(col,col+2):
                            cards.sprites()[LEVEL_COUNT[level - 1] + lrow * (6 - level + 1) + lcol].covered = True
                x = 70 + col * (20 + CARD_SIZE) + level * (20 + CARD_SIZE) / 2
                y = 130 + row * (20 + CARD_SIZE) + level * (20 + CARD_SIZE) / 2
                card = Card(cardtile[LEVEL_COUNT[level] + row*(6-level) + col],(x,y),level,row,col)
                cards.add(card)
    if DIFFICULTY_INDEX == 2:
        for i in range(2):
            for j in range(9):
                if i == 0:
                    x = i * 300 + 70 + j * 5
                    y = 65
                    card = Card(cardtile[90 + 9 * i + j], (x, y), 5, i, j)
                    cards.add(card)
                else:
                    x =  470 - j * 5
                    y = 65
                    card = Card(cardtile[90 + 9 * i + j], (x, y), 5, i, j)
                    cards.add(card)
    return cards

#消除卡片执行的操作
def destroycard(tiles,destype,totaltile):
    #关于选牌堆中各卡片的位置计算较为复杂，不好解释
    for i in range(len(tiles)):
        if tiles.sprites()[i].type == destype:
            tiles.sprites()[i].destroyed = True
            if tiles.sprites()[i].level > 0:
                for lrow in range(tiles.sprites()[i].row, tiles.sprites()[i].row + 2):
                    for lcol in range(tiles.sprites()[i].col, tiles.sprites()[i].col + 2):
                        totaltile.sprites()[LEVEL_COUNT[tiles.sprites()[i].level - 1] + lrow * (6 - tiles.sprites()[i].level + 1) + lcol].covered = False
    for card in tiles:
        if card.type == destype:
            tiles.remove(card)

pygame.init()

#将分数数据写进文件
def writefile(filepath,scb):
    with open(filepath, 'w') as file:
        for score in scb:
            file.write(f'{score}\n')

#更新新的分数
def updatescore(scb,newscore):
    scb.append(newscore)
    print(scb)
    scb = sorted(scb,reverse=True)
    return scb[:9]

#记分板场景
def scoreboard():
    isrunning = True
    frate = pygame.time.Clock()
    font = pygame.font.Font('fonts\msyh.ttc', 35)
    bg = pygame.transform.scale(pygame.image.load(r"images/bg.png"), (600, 720))
    backbutton = Button(4, "回到主菜单", 300, 650, 170, 50, 47, 15)
    group = pygame.sprite.Group()
    group.add(backbutton)
    scores = loadscore(SCORE_FILE_PATH)
    tableimg = pygame.transform.scale(pygame.image.load(r"images/table.png"),(540,640))
    while isrunning:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play()
        frate.tick(60)
        mouse_pos = pygame.mouse.get_pos()
        screen.blit(bg, (0, 0))
        screen.blit(tableimg, (30, 40))
        title = font.render('排行榜', True, (255,255,255))
        screen.blit(title, (600 // 2 - title.get_width() // 2, 65))
        #记分板读取显示思路由CHATGPT提供
        for i, score in enumerate(scores):
            entry_text = font.render(f'{i + 1}  分数：{score}', True, (59,59,59))
            screen.blit(entry_text, (200, 150 + i * 40))
        group.draw(screen)
        group.update(mouse_pos)
        pygame.display.flip()
        #事件判断
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                isrunning = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for button in group:
                    if button.rect.collidepoint(event.pos):
                        msg = button.doevent()
                        if msg == 4:
                            gamestart()
                            return

#游戏开始场景
def gamestart():
    global DIFFICULTY_INDEX

    pygame.mixer.music.set_volume(0.4)
    frate = pygame.time.Clock()
    diffbar = pygame.Surface((10, 50)) #难度标识，方便玩家辨认难度
    diffbar.fill((0, 255, 0))
    title = AnimImage(screen)
    title.loadimg("titlegif",362,177,7,43,119,100)
    group = pygame.sprite.Group()
    group.add(title)
    starting = True
    quitbutton = Button(1, "退出游戏", 300, 670, 150, 50, 40, 15)
    startbutton = Button(2,"开始游戏",300,600,150,50,40,15)
    dif1button = Button(5, "简单难度", 300, 530, 150, 50, 40, 15)
    dif2button = Button(6, "普通难度", 300, 460, 150, 50, 40, 15)
    dif3button = Button(7, "困难难度", 300, 390, 150, 50, 40, 15)
    scorebutton = Button(8, "查看排行榜", 300, 320, 170, 50, 47, 15)
    buttongroup = pygame.sprite.Group()
    buttongroup.add(startbutton,dif1button,dif2button,dif3button,scorebutton,quitbutton)
    #载入背景
    bg = pygame.transform.scale(pygame.image.load(r"images/bg.png"),(600,720))
    while starting:
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play()
        frate.tick(60)
        ticks = pygame.time.get_ticks()
        screen.fill((200, 200, 200))
        screen.blit(bg, (0, 0))
        group.update(ticks*1.6)
        group.draw(screen)
        mouse_pos = pygame.mouse.get_pos()
        buttongroup.draw(screen)
        buttongroup.update(mouse_pos)
        screen.blit(diffbar,(375,365 + (2 - DIFFICULTY_INDEX) * 70))
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                starting = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttongroup:
                    if button.rect.collidepoint(event.pos):
                        msg = button.doevent()
                        if msg == 2:
                            starting = False
                            main()
                        elif 5 <= msg <= 7:
                            DIFFICULTY_INDEX = msg - 5
                        elif msg == 8:
                            scoreboard()
                            return
                        elif msg == 1:
                            return

def main():
    #初始化各个项目
    restarting = False

    clearsound = pygame.mixer.Sound(f"sound\clear.wav")

    gamerunning = True

    clock = pygame.time.Clock()

    buttons = pygame.sprite.Group()

    backbutton = Button(4, "回到主菜单", 300, 30, 170, 50, 47, 15)
    buttons.add(backbutton)
    selectedtiles = pygame.sprite.Group()
    tiletype = []
    tiletypecount = [0] * 12
    cards = draw_cards()

    tableimg = pygame.transform.scale(pygame.image.load(r"images/table.png"),(540,640))

    credit = 0

    font = pygame.font.Font('fonts\msyh.ttc', 35)
    starttime = pygame.time.get_ticks()
    timepassed = DIFFICULTY[DIFFICULTY_INDEX][1]

    clicksound = pygame.mixer.Sound(r"sound\click.wav")

    cardboard = pygame.transform.scale(pygame.image.load(r"images/cardtile.png"),(600,140))

    while gamerunning:
        #循环背景音乐
        if not pygame.mixer.music.get_busy():
            pygame.mixer.music.play()
        timer = font.render(f"{timepassed}", True, (225, 225 * (timepassed/DIFFICULTY[DIFFICULTY_INDEX][1]),225 * (timepassed/DIFFICULTY[DIFFICULTY_INDEX][1])), None)
        clock.tick(GAME_FPS)
        #计时功能
        timepassed = DIFFICULTY[DIFFICULTY_INDEX][1] - (pygame.time.get_ticks() - starttime) // 1000
        if timepassed == 0 and credit != DIFFICULTY[DIFFICULTY_INDEX][0]:
            fail(credit)
            return
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                gamerunning = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                #点击卡片时
                for card in cards:
                    if card.rect.collidepoint(event.pos) and not card.selected and not card.covered:
                        # 卡片遮盖计算
                        if  5 > card.level > 0:
                            for lrow in range(card.row, card.row + 2):
                                for lcol in range(card.col, card.col + 2):
                                    cards.sprites()[
                                        LEVEL_COUNT[card.level - 1] + lrow * (6 - card.level + 1) + lcol].covered = False
                        elif card.level == 5 and card.col > 0:
                            cards.sprites()[
                                89 + card.row * 9 + card.col].covered = False
                        card.selected = True
                        clicksound.play()
                        #将卡片移向选卡堆
                        #选卡堆排序较为复杂，便不讲述
                        if tiletypecount[card.type - 1] == 0:
                            tiletype.append(card.type)
                            card.targetpos = (len(selectedtiles) * (CARD_SIZE + 10) + 60, 670)
                        else:
                            index = 0
                            for i in range(len(tiletype)):
                                if tiletype[i] == card.type:
                                    card.targetpos = (index * (CARD_SIZE + 10) + 60, 670)
                                    for j in range(len(selectedtiles)):
                                        if tiletypecount[card.type-1] == 2:
                                            for check in range(i,len(tiletype)):
                                                if selectedtiles.sprites()[j].type == tiletype[check]:
                                                    selectedtiles.sprites()[j].targetpos = (
                                                        selectedtiles.sprites()[j].targetpos[0] - 2 * (CARD_SIZE + 10),
                                                        670)
                                                    break
                                        else:
                                            for check in range(i,len(tiletype)):
                                                if selectedtiles.sprites()[j].type == tiletype[check]:
                                                    selectedtiles.sprites()[j].targetpos = (
                                                        selectedtiles.sprites()[j].targetpos[0] + (CARD_SIZE + 10), 670)
                                                    break
                                index += tiletypecount[tiletype[i]-1]
                        selectedtiles.add(card)
                        tiletypecount[card.type - 1] += 1
                        #卡片消除判断
                        if tiletypecount[card.type - 1] == 3:
                            destroycard(selectedtiles,card.type,cards)
                            tiletype.remove(card.type)
                            tiletypecount[card.type - 1] = 0
                            clearsound.play()
                            credit += 3
                        if len(selectedtiles) > 7:
                            fail(credit)
                            return
                #胜利判断
                if credit == DIFFICULTY[DIFFICULTY_INDEX][0]:
                    win(credit,timepassed)
                    return
                #按钮事件监听
                for button in buttons:
                    if button.rect.collidepoint(event.pos):
                        msg = button.doevent()
                        if msg == 2:
                            gamerunning = False
                            main()
                        elif msg == 4:
                            pygame.mixer.music.load(r"music\maintheme.mp3")
                            gamestart()
                            return
        #渲染相关
        screen.fill((200,200,200))
        screen.blit(tableimg, (30, 40))
        screen.blit(cardboard, (0, 610))
        mouse_pos = pygame.mouse.get_pos()
        cards.update(mouse_pos,cards)
        cards.draw(screen)
        screen.blit(timer,(300 - timer.get_width() // 2,66))
        buttons.draw(screen)
        buttons.update(mouse_pos)
        pygame.display.flip()
        if restarting:
            main()
            return
#胜利场景
def win(score,timeremain):
    #各个参数初始化
    font = pygame.font.Font('fonts\msyh.ttc', 35)
    scoredisplay = font.render(f"得分：{score + timeremain}", True, (152,142,225), None)
    pygame.mixer.music.load(r"music\win.wav")
    pygame.mixer.music.set_volume(1)
    winning = True
    tickcount = 0
    winimg = pygame.transform.scale(pygame.image.load(r"images\win.png"), (600, 720))
    winsound = pygame.mixer.Sound("sound\win.wav")
    backbutton = Button(4, "回到主菜单", 300, 600, 170, 50,47,15)
    buttongroup = pygame.sprite.Group()
    buttongroup.add(backbutton)
    particlegruop = pygame.sprite.Group()

    #分数文件记录
    scb = loadscore(SCORE_FILE_PATH)

    scb = updatescore(scb, score + timeremain)

    writefile(SCORE_FILE_PATH, scb)
    winsound.play()
    pygame.mixer.music.stop()
    while winning:
        mouse_pos = pygame.mouse.get_pos()
        ticks = pygame.time.get_ticks()
        tickcount += ticks
        screen.blit(winimg,(0,0))
        #产生有物理效果的粒子，模拟烟花特效
        if tickcount > 200:
            newparticle = Particle(randint(0, 600), 0)
            particlegruop.add(newparticle)
        particlegruop.update()
        particlegruop.draw(screen)
        buttongroup.draw(screen)
        buttongroup.update(mouse_pos)
        screen.blit(scoredisplay, (225, 480))
        pygame.display.flip()
        #事件监听
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                winning = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttongroup:
                    if button.rect.collidepoint(event.pos):
                        msg = button.doevent()
                        if msg == 2:
                            winning = False
                            main()
                        elif msg == 4:
                            pygame.mixer.music.load(r"music\maintheme.mp3")
                            gamestart()
                            return

#失败场景
def fail(score):
    #各参数初始化
    font = pygame.font.Font('fonts\msyh.ttc', 35)
    scoredisplay = font.render(f"得分：{score}", True, (225, 225, 225), None)
    frate = pygame.time.Clock()
    failimg = pygame.transform.scale(pygame.image.load(r"images\lose.png"),(600,720))
    failsound = pygame.mixer.Sound("sound\lose.wav")
    gamefail = True
    buttongroup = pygame.sprite.Group()
    restartbutton = Button(3, "重新开始", 300, 600, 170, 50,40,15)
    backbutton = Button(4, "回到主菜单", 300, 670, 170, 50, 47, 15)
    buttongroup.add(restartbutton,backbutton)
    failsound.play()
    pygame.mixer.music.stop()
    while gamefail:
        frate.tick(60)
        screen.blit(failimg, (0, 0))
        mouse_pos = pygame.mouse.get_pos()
        buttongroup.draw(screen)
        buttongroup.update(mouse_pos)
        screen.blit(scoredisplay, (225, 480))
        pygame.display.flip()
        #事件监听
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttongroup:
                    if button.rect.collidepoint(event.pos):
                        msg = button.doevent()
                        if msg == 3:
                            main()
                            return
                        elif msg == 4:
                            pygame.mixer.music.load(r"music\maintheme.mp3")
                            gamestart()
                            return
            elif event.type == pygame.QUIT:
                gamefail = False
    pygame.quit()

#程序启动时打开游戏开始场景
if __name__ == "__main__":
    gamestart()