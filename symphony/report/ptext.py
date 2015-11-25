# Copyright 2015 Tata Consultancy Services, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
Text Creator
"""

from reportlab.lib.enums import TA_JUSTIFY,TA_CENTER
from reportlab.lib import *
from reportlab.lib.pagesizes import *
from reportlab.platypus import *
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import Color, blue, red, green, yellow, black , cyan, gray, lavenderblush
import pdf

def create_ptext(ptext_data,size): 
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    ptext = '<font size=%s>%s</font>' %(size,ptext_data) 
    ftext = Paragraph(ptext, styles["Normal"])
    return ftext


def create_pctext(ptext_data,size):
    sty = ParagraphStyle(name='CENTER', alignment=TA_CENTER)
    ptext = '<font size=%s>%s</font>' %(size,ptext_data)
    ftext = Paragraph(ptext, style=sty)
    return ftext

