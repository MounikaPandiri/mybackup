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
Graph Creator
"""

from reportlab.graphics.charts.linecharts import HorizontalLineChart     
from reportlab.graphics.shapes import Drawing
from reportlab.lib.colors import Color, PCMYKColor
from reportlab.lib import colors,styles
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.charts.legends import LineLegend
from reportlab.lib.colors import Color, blue, red, green, yellow, black , cyan, gray, lightblue
import pdf
import utils


def create_graph(graph_data): 
    color=[green,red,blue,yellow,black]
    color_index = 0
    line_chart = Drawing(400, 200)
    data_length=len(graph_data["data"])
    lc = HorizontalLineChart()
    lc.x = 50
    lc.y = 50
    lc.height = 125
    lc.width = 300
    lc.data = graph_data["data"]
    lc.fillColor=lightblue	
    lc.joinedLines = 1
    lc.categoryAxis.categoryNames = list(graph_data["label"][0])
    lc.categoryAxis.labels.boxAnchor ='n'
    lc.valueAxis.valueMin = utils.get_least_pt(graph_data["data"])
    lc.valueAxis.valueMax = utils.get_max_pt(graph_data["data"])
    lc.valueAxis.valueStep = (lc.valueAxis.valueMax - lc.valueAxis.valueMin)/10 if (lc.valueAxis.valueMax - lc.valueAxis.valueMin) > 40 else (lc.valueAxis.valueMax - lc.valueAxis.valueMin)/5
   
    for i in xrange(data_length):
        lc.lines[i].strokeWidth = 2
        lc.lines[i].strokeColor = color[i]
    
    line_chart.add(lc)
    line_leg = LineLegend() 
    line_leg.boxAnchor       = 'sw'
    line_leg.x               = 100
    line_leg.y               = -1
    
    line_leg.columnMaximum   = 1
    line_leg.yGap            = 0
    line_leg.deltax          = 50
    line_leg.deltay          = 0
    line_leg.dx              = 10
    line_leg.dy              = 1.5
    line_leg.fontSize        = 10
    line_leg.alignment       = 'right'
    line_leg.dxTextSpace     = 5
    line_leg.colorNamePairs  = [(color[i],graph_data["legend"][0][i]) for i in xrange(data_length)]
    line_chart.add(line_leg) 
    
    return line_chart

