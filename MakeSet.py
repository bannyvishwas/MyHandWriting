import sys,pygame
from pygame.locals import *
from pygame import Color
import os
from PIL import Image, ImageEnhance

pygame.init()

#Variables
z=0
actdirectory="images/letters"
no_set=0
actset=0
letter_act_index=0
letterlist="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789,.?{}()-_+=*&^%@<>|/'\"\\;:"


screen = pygame.display.set_mode((500,350))
screen.fill((255,255,255))

pygame.display.set_caption('My Hand Writing')
ico = pygame.image.load('images/icon.png')
pygame.display.set_icon(ico)

##pygame.draw.rect(screen, (255,255,255) , (10,10,200,300))
mydraw = pygame.Surface((200, 300), pygame.SRCALPHA, 32)
##pygame.draw.line(screen, (163,163,163) , (10,110), (210,110),1)
##pygame.draw.line(screen, (163,163,163) , (10,210), (210,210),1)
##pygame.draw.rect(screen, (0,0,0) , (10,10,200,300),2)


#Program label
font = pygame.font.Font('freesansbold.ttf',18)
text = font.render("Text To Hand Writing", True, (62, 97, 219))
screen.blit(text, (260, 30))

#button coordinates
b1=(220,65,250,35)
b2=(220,110,250,35)
b3=(220,155,250,35)

#button color
noactcolor=(164, 170, 164)
actcolor=(184, 238, 57)
black=(0,0,0)
empty = Color(0,0,0,0)

#text coordinates
t1=(320, 75)
t2=(320, 120)
t3=(300, 165)

#Error label
t4=(100,320)
dt=(65, 320)
dtxt="Draw --> A"
font1 = pygame.font.Font('freesansbold.ttf',20)
dtext = font1.render(dtxt, True, black)

#draw letter label

screen.blit(dtext,dt)

#text font size/style
txtfont = pygame.font.Font('freesansbold.ttf',15)
txt1 = txtfont.render("Create", True, black)
txt2 = txtfont.render("Clear", True, black)
txt3 = txtfont.render("Create New Set", True, black)


#Developer Label
font = pygame.font.Font('freesansbold.ttf',40)
text = font.render("Bug Boy", True, (62, 97, 219))
screen.blit(text, (280, 210))
font = pygame.font.Font('freesansbold.ttf',10)
text = font.render("(Contribute Here)", True, (240, 40, 90))
screen.blit(text, (320, 260))
text = font.render("https://github.com/bannyvishwas2020/MyHandWriting", True, (62, 97, 219))
screen.blit(text, (220, 280))

screen.blit(mydraw, (10, 10))

brush = pygame.image.load("images/brush.png")
brush = pygame.transform.scale(brush,(15,15))

pygame.display.update()
clock=pygame.time.Clock()


def display_mess():
    global dtxt
    pygame.draw.rect(screen, (255,255,255) , (65,320,120,100))
    dtext = font1.render(dtxt, True, black)
    screen.blit(dtext, dt)
    pygame.display.update()
    
def check_directory():
    global actdirectory
    sdir = os.path.isdir(actdirectory)
    if sdir: 
        cdir=os.listdir("images/letters")
        no_set=len(cdir)
        actset=no_set+1
        actdirectory="images/letters/set{}".format(actset)
        os.mkdir(actdirectory)
        os.mkdir(actdirectory+"/blue")
        os.mkdir(actdirectory+"/black")
    else:
        os.mkdir("images/letters")
        actset=1
        actdirectory="images/letters/set{}".format(actset)
        
def create_letter():
    global actdirectory
    global letter_act_index
    global dtxt
    letter=ord(letterlist[letter_act_index])
    imfile="{}/blue/{}.png".format(actdirectory,letter)
    #Blue Letter
    pygame.image.save(mydraw, imfile)
    
    #black letter
    im = Image.open(imfile)
    enhancer = ImageEnhance.Brightness(im)
    factor = 0.35
    im_output = enhancer.enhance(factor)
    im_output.save("{}/black/{}.png".format(actdirectory,letter))
    
    letter_act_index+=1
    dtxt="Draw --> {}".format(letterlist[letter_act_index])

def reset_surface():
    pygame.draw.rect(screen, (255,255,255) , (10,10,200,300))
    mydraw.fill(empty)
    pygame.draw.line(screen, (163,163,163) , (10,110), (210,110),1)
    pygame.draw.line(screen, (163,163,163) , (10,210), (210,210),1)
    pygame.draw.rect(screen, (0,0,0) , (10,10,200,300),2)


def btn_reset():
    #draw buttons
    pygame.draw.rect(screen, noactcolor , b1)
    pygame.draw.rect(screen, noactcolor , b2)
    pygame.draw.rect(screen, noactcolor , b3)

    #write Text
    screen.blit(txt1, t1)
    screen.blit(txt2, t2)
    screen.blit(txt3, t3)
    pygame.display.update()
        
        
def btn_clicked(btnid):
    btn_reset()
    if btnid==1:
        pygame.draw.rect(screen, actcolor , b1)
        screen.blit(txt1, t1)
    elif btnid==2:
        pygame.draw.rect(screen, actcolor , b2)
        screen.blit(txt2, t2)
    else:
        pygame.draw.rect(screen, actcolor , b3)
        screen.blit(txt3, t3)
    pygame.display.update()
        
def mouse_clicked(x,y):
    global letter_act_index
    global dtxt
    if(x>220 and y>65 and x<470 and y<100):
        btn_clicked(1)
        create_letter()
        reset_surface()
        display_mess()
    elif(x>220 and y>110 and x<470 and y<145):
        btn_clicked(2)
        reset_surface()
    elif(x>220 and y>155 and x<470 and y<190):
        btn_clicked(3)
        check_directory()
        dtxt="Draw --> A"
        letter_act_index=0
        display_mess()
    

check_directory()
reset_surface()
display_mess()
btn_reset()

while 1:
    clock.tick(30)
    x,y=pygame.mouse.get_pos()
    click = pygame.mouse.get_pressed()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            sys.exit()
        elif event.type == MOUSEBUTTONDOWN:
            z = 1
        elif event.type == MOUSEBUTTONUP:
            z = 0
            mouse_clicked(x,y)
            pygame.display.update()

        if z == 1:
            mydraw.blit(brush,(x-14,y-14))
            screen.blit(mydraw, (10, 10))
            pygame.display.update()
