#!/usr/bin/env python3
# Coded By BugBoy : Github(https://github.com/bannyvishwas2020)
import random
import argparse

parser = argparse.ArgumentParser(description='Convert text to a handwritten page')
parser.add_argument('--infile',
                    default='content.txt',
                    dest='inputfile',
                    help='path to input text file (defaults to ./content.txt',
                    )
parser.add_argument('--lettercolor',
                    default='blue',
                    dest='letter_color',
                    help='Color of normal/default text',
                    )
parser.add_argument('--letterset',
                    default='set0',
                    dest='letter_set',
                    help='Handwriting character set',
                    )
parser.add_argument('--background',
                    default='images/texture.png',
                    dest='bgimage',
                    help='Background texture for "paper"',
                    )
parser.add_argument('--outfile',
                    default='page.html',
                    dest='outputfile',
                    help='path to input text file (defaults to ./content.txt',
                    )
args = parser.parse_args()

trcolor = False
letter_type = ""

htmlc = [
    "<html><head><style>.lines{width:100%;height:auto;float:left;}"
    "#paper{background:white;"
    "background-image:url('"+args.bgimage+"');height:auto;float:left;"
    "padding:50px 50px;width:90%;}img,span{height:25px;width:10px;"
    "float:left;margin-top:5px;margin-bottom:10px;}"
    ".clblack{filter:brightness(30%);}.clblue{filter:brightness(100%);"
    "}</style></head><body><div id='paper'>"]


with open(args.inputfile, 'r') as textfile:
    for line in textfile:

        # Strips the newline character
        curst = line.strip()
        htmlc.append('<div class="lines">')
        for ch in curst:
            # get char ASCII Code of char
            chcode = ord(ch)
            # max 10 sets of letters
            random_letter = round(random.random()*10)
            # enable the below statement if 10 sets of letters available
            # letter_set="set{}".format(random_letter)
            if(chcode == 35):
                if(trcolor):
                    args.letter_color = "blue"
                    trcolor = False
                else:
                    args.letter_color = "black"
                    trcolor = True
            elif(chcode >= 65 and chcode <= 90):
                letter_type = "caps"
                ch = ch.lower()
            elif(chcode >= 97 and chcode <= 177):
                letter_type = "small"
            elif(chcode >= 48 and chcode <= 57):
                letter_type = "others"
                ch = "{}".format(chcode)
            elif(chcode == 32 or chcode == 36):
                htmlc.append("<span></span>")
            else:
                letter_type = "others"
                ch = "{}".format(chcode)
            if(chcode != 35 and chcode != 32 and chcode != 36):
                htmlc.append("<img src='images/letters/{}/{}/{}/{}.png'/>".format(
                    args.letter_set, args.letter_color, letter_type, ch))
        htmlc.append('</div>')

htmlc.append('</div></body></html>')

with open(args.outputfile, 'w') as page_html:
    page_html.writelines(htmlc)
