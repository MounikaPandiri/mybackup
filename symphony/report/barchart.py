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
Bar Chart Creator

"""

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.lib.colors import Color, PCMYKColor
from reportlab.lib import colors,styles
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.charts.legends import LineLegend
from reportlab.lib.colors import Color, blue, red, green, yellow, black , cyan, gray, lightblue
import pdf


def create_barchart(barchart_data):
    color=[green,red,blue,yellow,black]
    data_length=len(barchart_data["data"])
    bar_chart = Drawing(400, 200)
    bc = VerticalBarChart()
    bc.x = 50
    bc.y = 50
    bc.height = 125
    bc.width = 300
    bc.data = barchart_data["data"]
    bc.fillColor=lightblue
    bc.strokeColor = colors.black
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = 50
    bc.valueAxis.valueStep = 10
    bc.categoryAxis.labels.dx = 8
    bc.categoryAxis.labels.dy = -2
    bc.categoryAxis.labels.angle = 30
    bc.categoryAxis.categoryNames = list(barchart_data["label"][0])
    for i in xrange(data_length):
        bc.bars[i].fillColor = color[i]
    bar_chart.add(bc)


    ###legend#### 
    bar_leg = LineLegend()
    bar_leg.boxAnchor       = 'sw'
    bar_leg.x               = 100
    bar_leg.y               = -1

    bar_leg.columnMaximum   = 1
    bar_leg.yGap            = 0
    bar_leg.deltax          = 50
    bar_leg.deltay          = 0
    bar_leg.dx              = 10
    bar_leg.dy              = 1.5
    bar_leg.fontSize        = 10
    bar_leg.alignment       = 'right'
    bar_leg.dxTextSpace     = 5
    bar_leg.colorNamePairs  = [(color[i],barchart_data["legend"][0][i]) for i in xrange(data_length)]
    bar_chart.add(bar_leg) 
    return bar_chart
