#Coded By BugBoy : Github(https://github.com/bannyvishwas2020)
import random
textfile = open('content.txt', 'r')
Lines = textfile.readlines()
letter_color="clblue"
letter_set="set0"
trcolor=False
letter_type=""
htmlc=["<html><head><style>.lines{width:100%;height:auto;float:left;}#paper{background:white;background-image:url('images/texture.png');height:auto;float:left;padding:50px 50px;width:90%;}img,span{height:25px;width:10px;float:left;margin-top:5px;margin-bottom:10px;}.clblack{filter:brightness(30%);}.clblue{filter:brightness(100%);}</style></head><body><div id='paper'>"]
# Strips the newline character 
for line in Lines: 
    curst=line.strip()
    htmlc.append('<div class="lines">')
    for ch in curst:
        #get char ASCII Code of char
        chcode=ord(ch)
        #max 10 sets of letters 
        random_letter=round(random.random()*10)
        #enable the below statement if 10 sets of letters available
        #letter_set="set{}".format(random_letter)
        if(chcode==35):
            if(trcolor):
                letter_color="clblue"
                trcolor=False
            else:
                letter_color="clblack"
                trcolor=True
        elif(chcode>=65 and chcode<=90):
            letter_type="caps"
            ch=ch.lower()
        elif(chcode>=97 and chcode<=177):
            letter_type="small"
        elif(chcode>=46 and chcode<=63):
            letter_type="others"
            ch="{}".format(chcode)
        elif(chcode==32 or chcode==36):
            htmlc.append("<span></span>")
        else:
            letter="others"
            ch="{}".format(chcode)
        if(chcode!=35 and chcode!=32 and chcode!=36):
            htmlc.append("<img class='{}' src='images/letters/{}/{}/{}.png'/>".format(letter_color,letter_set,letter_type,ch))
    htmlc.append('</div>')
textfile.close()
htmlc.append('</div></body></html>')
page_html = open('page.html', 'w') 
page_html.writelines(htmlc) 
page_html.close() 
