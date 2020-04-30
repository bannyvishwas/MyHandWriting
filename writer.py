# Coded By BugBoy : Github(https://github.com/bannyvishwas2020)
import random
import os

letter_color = "blue"
letter_set = "set0"
trcolor = False
totalset=len(os.listdir("images/letters"))+1

htmlc = [
    "<html><head><style>.lines{width:100%;height:auto;float:left;}#paper{background:white;background-image:url('images/texture.png');height:auto;float:left;padding:50px 50px;width:90%;}img,span{height:25px;width:15px;float:left;margin-top:5px;margin-bottom:10px;}.clblack{filter:brightness(30%);}.clblue{filter:brightness(100%);}</style></head><body><div id='paper'>"]

with open('content.txt', 'r') as textfile:
    for line in textfile:
        # Strips the newline character
        curst = line.strip()
        htmlc.append('<div class="lines">')
        for ch in curst:
            # get char ASCII Code of char
            chcode = ord(ch)

            #select Random set
            random_letter = random.randrange(1,totalset)
            letter_set="set{}".format(random_letter)
            
            if(chcode == 35):
                if(trcolor):
                    letter_color = "blue"
                    trcolor = False
                else:
                    letter_color = "black"
                    trcolor = True
            elif(chcode == 32 or chcode == 36):
                htmlc.append("<span></span>")
                
            if(chcode != 35 and chcode != 32 and chcode != 36):
                htmlc.append("<img src='images/letters/{}/{}/{}.png'/>".format(
                    letter_set, letter_color, chcode))
        htmlc.append('</div>')

htmlc.append('</div></body></html>')

with open('page.html', 'w') as page_html:
    page_html.writelines(htmlc)
