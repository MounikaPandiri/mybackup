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
Table Creator

"""
 
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.units import inch
from reportlab.lib import colors,styles
from reportlab.lib.pagesizes import letter,A4,inch,cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Table,TableStyle,Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import Color, PCMYKColor  
import pdf


def create_table(table_data):
    #usage_data = [['MULTI_NODE','Setup-2', ['vHS','vBono','vEllis','vHomer'],'2','2048', '26','2']]
    usage_data = table_data['data']
    doc = SimpleDocTemplate('temp.pdf', pagesize=letter,rightMargin=72,leftMargin=72,topMargin=72,bottomMargin=18)
    rowheight = []
    data = []  
    colwid = []
    for key in table_data['header']:
        colwid.append(len(key)*.225*cm)
    data.append(table_data['header'])
    rowheight.append(15)
    for node in usage_data:
        temp_data = []
        flag = 0 
        for inner_node in node:
            if type(inner_node) is list :
               if len(inner_node) > 0:
                   rowheight.append(15*len(inner_node))
               else:
                   rowheight.append(15)
               config = "\n" 
               for key in inner_node:
                   config = config + key + "\n"
               temp_data.append(config)
            else:
               flag = flag + 1   
               temp_data.append(inner_node)
               continue 
        if flag == len(node):
            rowheight.append(15)   
        data.append(temp_data)
    
    #t=Table(data,colWidths=[4.2 * cm, 2 * cm, 2 * cm,2 * cm, 2* cm,2 * cm],rowHeights=rowheight)
    t=Table(data,colWidths=colwid,rowHeights=rowheight)
    width, height = A4
    t.setStyle(TableStyle([('FONTSIZE', (0,0), (-1, -1), 7),
                           ('TEXTCOLOR',(0,1),(-1,-1),colors.blue),
                           ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                           ('ALIGN',(0,0),(-1,-1),'CENTER'),
                          # ('ALIGN',(1,1),(1,-1),'LEFT'),
                           ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                           #('INNERGRID', (2,0), (-3,0), 0.5, colors.white),
                           ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                           ]))
    t.wrapOn(doc, 600, 200)
    return t
    #pdf.genpdf(t)

