import pygame
import time
import random
from pygame.sprite import Sprite

SCREEN_WIDTH=700
SCREEN_HEIGHT=500
BG_COLOR=pygame.Color(0, 0, 0)
TEXT_COLOR=pygame.Color(255, 0, 0)
class BaseItem(Sprite):
    def __init__(self, color, width, height):
        # Call the parent class (Sprite) constructor
        pygame.sprite.Sprite.__init__(self)

class MainGame():
    window = None
    my_tank = None
    #存储坦克列表
    enemyTankList = []
    enemyTankCount = 5

    myBulletList = []

    enemyBulietList = []

    explodeList=[]

    def __init__(self):
        pass

    def startGame(self):
        print("start game")
        pygame.display.init()
        MainGame.window=pygame.display.set_mode([SCREEN_WIDTH,SCREEN_HEIGHT])
        pygame.display.set_caption("坦克大战")
        MainGame.my_tank = Tank(350, 250)

        #初始化敌方坦克
        self.CreateEnemyTank()

        while True:
            time.sleep(0.003)
            #获取事件
            MainGame.window.fill(BG_COLOR)
            self.getEvent()
            MainGame.window.blit(self.getTextSuface("敌方坦克数量%d"%len(MainGame.enemyTankList)),(10,10))
            MainGame.my_tank.displayTank()

            self.blitMyBullet()

            self.blitEnemyTank()

            self.blitEnemyBuliet()

            self.blitExplode()

            if not MainGame.my_tank.stop :
                MainGame.my_tank.move()

            pygame.display.update()
            pygame.display.flip()

    def CreateEnemyTank(self):
        top = 100
        for i in range(MainGame.enemyTankCount):
            left = random.randint(0,600)
            speed = 1
            enemy= EnemyTank(left, top , speed)
            MainGame.enemyTankList.append(enemy)

    def blitEnemyTank(self):
        for et in MainGame.enemyTankList:
            if et.alive:
                et.displayTank()
                et.randMove()
                eb = et.shot()
                if eb :
                    MainGame.enemyBulietList.append(eb)
            else:
                MainGame.enemyTankList.remove(et)

    def blitMyBullet(self):
        for myBullet in MainGame.myBulletList:
            if myBullet.alive:
                myBullet.displayBullet()
                myBullet.move()
                myBullet.myBullet_hit_enemyTank()
            else:
                MainGame.myBulletList.remove(myBullet)

    def blitEnemyBuliet(self):
        for eb in MainGame.enemyBulietList:
            if eb.alive:
                eb.displayBullet()
                eb.move()
            else:
                MainGame.enemyBulietList.remove(eb)
    def blitExplode(self):
        for explode in MainGame.explodeList:
            if explode.live :
                explode.displayExplode()
            else:
                MainGame.explodeList.remove(explode)

    def endGame(self):
        print("exit")
        exit()

    #左上角文字
    def getTextSuface(self,text):
        pygame.font.init()
        #print(pygame.font.get_fonts())
        font = pygame.font.SysFont('kaiti',18)
        txt = font.render(text, True, TEXT_COLOR)
        return txt

    def getEvent(self):
        #获取所有的事件
        eventList= pygame.event.get()
        for event in eventList:
            if event.type == pygame.QUIT:
                self.endGame()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    print("Key LEFT")
                    MainGame.my_tank.direction='L'
                    MainGame.my_tank.stop = False
                    #MainGame.my_tank.move()
                elif event.key == pygame.K_RIGHT:
                    print("Key RIGHT")
                    MainGame.my_tank.direction = 'R'
                    MainGame.my_tank.stop = False
                    #MainGame.my_tank.move()
                elif event.key == pygame.K_UP:
                    print("Key UP")
                    MainGame.my_tank.direction = 'U'
                    MainGame.my_tank.stop = False
                    #MainGame.my_tank.move()
                elif event.key == pygame.K_DOWN:
                    print("Key DOWN")
                    MainGame.my_tank.direction = 'D'
                    MainGame.my_tank.stop = False
                    #MainGame.my_tank.move()
                elif event.key == pygame.K_SPACE:
                    print("Fire")
                    myBullet = Bullet(MainGame.my_tank)
                    MainGame.myBulletList.append(myBullet)

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_UP  or event.key == pygame.K_DOWN or event.key == pygame.K_LEFT  or event.key == pygame.K_RIGHT:
                    MainGame.my_tank.stop = True

class Tank(BaseItem):
    def __init__(self, left, top):
        self.images = {
            'U': pygame.image.load("imgs/p1tankU.gif"),
            'D': pygame.image.load('imgs/p1tankD.gif'),
            'L': pygame.image.load('imgs/p1tankL.gif'),
            'R': pygame.image.load('imgs/p1tankR.gif')
        }
        self.direction = 'D'
        self.image = self.images[self.direction]

        self.rect = self.image.get_rect()
        self.rect.left = left
        self.rect.top = top

        self.stop = True

        self.speed = 1

    def move(self):
        if self.direction == 'L':
            if self.rect.left >0 :
                self.rect.left -= self.speed
        elif self.direction == 'U':
            if self.rect.top > 0:
                self.rect.top -= self.speed
        elif self.direction == 'D':
            if self.rect.top  +self.rect.height <SCREEN_HEIGHT :
                self.rect.top += self.speed
        elif self.direction == 'R':
            if self.rect.left + self.rect.width < SCREEN_WIDTH:
                self.rect.left += self.speed

    def shot(self):
        num = random.randint(1,1000)
        if num < 7 :
            return Bullet(self)

    def displayTank(self):
        self.image = self.images[self.direction]
        MainGame.window.blit(self.image,self.rect)

class MyTank(Tank):

    def __init__(self):
        pass

class EnemyTank(Tank):
    def __init__(self,left,top,speed):
        self.images={
            'U': pygame.image.load("imgs/enemy1U.gif"),
            'D': pygame.image.load('imgs/enemy1D.gif'),
            'L': pygame.image.load('imgs/enemy1L.gif'),
            'R': pygame.image.load('imgs/enemy1R.gif')
        }
        self.direction = self.randDirection()
        self.image=self.images[self.direction]
        self.rect = self.image.get_rect()

        self.rect.left = left
        self.rect.top = top
        self.speed = speed

        self.flag = True
        self.setp = 10
        self.alive = True

    def randDirection(self):
        num = random.randint(1,4)
        if num == 1:
            return 'U'
        elif num == 2:
            return 'D'
        elif num == 3:
            return 'L'
        elif num == 4:
            return 'R'

    def randMove(self):
        if self.setp <= 0:
            self.direction = self.randDirection()
            self.setp =  random.randint(60,140)
        else:
            self.move()
            self.setp -= 1

class Bullet(BaseItem):
    def __init__(self,tank):
        self.image = pygame.image.load("imgs/enemymissile.gif")

        self.direction = tank.direction

        self.rect = self.image.get_rect()

        if self.direction == 'U':
            self.rect.left = tank.rect.left + (tank.rect.width-self.rect.width)/2
            self.rect.top = tank.rect.top - self.rect.height
        elif self.direction == 'D':
            self.rect.left = tank.rect.left + tank.rect.width / 2 - self.rect.width / 2
            self.rect.top = tank.rect.top + tank.rect.height
        elif self.direction == 'L':
            self.rect.left = tank.rect.left - self.rect.width / 2 - self.rect.width / 2
            self.rect.top = tank.rect.top + tank.rect.width / 2 - self.rect.width / 2
        elif self.direction == 'R':
            self.rect.left = tank.rect.left + tank.rect.width
            self.rect.top = tank.rect.top + tank.rect.width / 2 - self.rect.width / 2

        self.speed = 2
        self.alive = True

    def move(self):
        if self.direction == 'U':
            if self.rect.top > 0:
                self.rect.top -= self.speed
            else:
                self.alive=False
        elif self.direction == 'R':
            if self.rect.left + self.rect.width < SCREEN_WIDTH:
                self.rect.left += self.speed
            else:
                self.alive=False
        elif self.direction == 'D':
            if self.rect.top + self.rect.height < SCREEN_HEIGHT:
                self.rect.top += self.speed
            else:
                self.alive=False
        elif self.direction == 'L':
            if self.rect.left > 0:
                self.rect.left -= self.speed
            else:
                self.alive=False

    def displayBullet(self):
        MainGame.window.blit(self.image,self.rect)
        print(self.rect.left)
        print(self.rect.top)

    def myBullet_hit_enemyTank(self):
        for enemyTank in MainGame.enemyTankList:
            if pygame.sprite.collide_rect(enemyTank,self):
                enemyTank.alive = False
                self.alive = False
                explode = Explode(enemyTank)
                #displayExplode()
                MainGame.explodeList.append(explode)

class Wall():
    def __init__(self):
        pass

    def display(self):
        pass

class Explode():
    def __init__(self, tank):
        self.rect= tank.rect
        self.images=[
            pygame.image.load("imgs/blast0.gif"),
            pygame.image.load("imgs/blast1.gif"),
            pygame.image.load("imgs/blast2.gif"),
            pygame.image.load("imgs/blast3.gif"),
            pygame.image.load("imgs/blast4.gif"),
        ]

        self.step = 0
        self.image = self.images[self.step]
        self.live = True

    def displayExplode(self):
        if self.step < len(self.images):
            self.image = self.images[self.step]
            self.step += 1
            MainGame.window.blit(self.image,self.rect)
        else:
            self.live = False
            self.step = 0

class Music():

    def __init__(self):
        pass

    def play(self):
        pass

if __name__ == '__main__':
    MainGame().startGame()