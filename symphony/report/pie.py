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
Pie Creator

"""

from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib.colors import Color, PCMYKColor
from reportlab.lib import colors,styles
import pdf


def create_pie(pie_data):
    pie_chart = Drawing(400, 200)
    pc = Pie()
    pc.x = 65
    pc.y = 15
    pc.width = 100
    pc.height = 100
    pc.data = pie_data["data"]     	     
    pc.labels = list(pie_data["label"][0]) 
    pc.slices.strokeWidth=0.5
    pc.slices[3].popout = 10
    pc.slices[3].strokeWidth = 2
    pc.slices[3].strokeDashArray = [2,2]
    pc.slices[3].labelRadius = 1.75
    pc.slices[3].fontColor = colors.red
    pie_chart.add(pc)
    return pie_chart

