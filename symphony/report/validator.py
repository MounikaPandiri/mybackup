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
Result Data Validator

"""

FAIL = "FAIL"
PASS = "PASS"
TABLE_KEYS = ["header","data"]
PIE_KEYS = ["label","data","legend"]
CHART_KEYS = ["label","data","legend"]

def validate_table_data(table_data):
    result = []
    if type(table_data) is not dict:
        result.append(FAIL)
        result.append("Dict is required")
        return result
    if len(table_data) != 2:
        result.append(FAIL)
        result.append("Dict size should be 2")
        return result
    for key in TABLE_KEYS:
        if key not in table_data.keys():
            result.append(FAIL)
            result.append(key + " is required")
            return result
        if type(table_data[key]) is not list:
            result.append(FAIL)
            result.append(key + " should be a list")
            return result 
        if table_data[key] == None:
            result.append(FAIL)
            result.append(key + " blank field")
            return result
        if len(table_data[key]) <= 0:
            result.append(FAIL)
            result.append(key + " blank field")
            return result
    if type(table_data['data'][0]) is not list:
        result.append(FAIL)
        result.append("data should be list")
        return result
    for a in table_data['data']:
        if len(a) != len(table_data['header']):
            result.append(FAIL)
            result.append("header and data fields mismatch")
            return result
        else:
            continue
    result.append(PASS)         
    return result

def validate_chart_data(chart_data):
    result = []
    if type(chart_data) is not dict:
        result.append(FAIL)
        result.append("Dict is required")
        return result
    if len(chart_data) != 3:
        result.append(FAIL)
        result.append("Dict size should be 3")
        return result
    for key in CHART_KEYS:
        if key not in chart_data.keys():
            result.append(FAIL)
            result.append(key + " is required")
            return result
        if type(chart_data[key]) is not list:
            result.append(FAIL)
            result.append(key + " should be a list")
            return result
        if type(chart_data[key][0]) is not tuple:
            result.append(FAIL)
            result.append(key + " should be a tuple inside list")
            return result
        if chart_data[key][0] == None:
            result.append(FAIL)
            result.append(key + " blank field")
            return result
        if len(chart_data[key][0]) <= 0:
            result.append(FAIL)
            result.append(key + " blank field")
            return result
    if len(chart_data['label'][0]) != len(chart_data['data'][0]):
        result.append(FAIL)
        result.append("label and data fields mismatch")
        return result
    if len(chart_data['legend'][0]) != len(chart_data['data']):
        result.append(FAIL)
        result.append("legend and data fields mismatch")
        return result
    result.append(PASS)
    return result
    print chart_data
    pass


def validate_pie_data(pie_data):
    result = []
    if type(pie_data) is not dict:
        result.append(FAIL)
        result.append("Dict is required")
        return result
    if len(pie_data) != 3:
        result.append(FAIL)
        result.append("Dict size should be 3")
        return result
    for key in PIE_KEYS:
        if key not in pie_data.keys():
            result.append(FAIL)
            result.append(key + " is required")
            return result
        if type(pie_data[key]) is not list:
            result.append(FAIL)
            result.append(key + " should be a list")
            return result
        if pie_data[key] == None:
            result.append(FAIL)
            result.append(key + " blank field")
            return result
        if len(pie_data[key]) <= 0:
            result.append(FAIL)
            result.append(key + " blank field")
            return result
    if len(pie_data['label']) != len(pie_data['data']):
        result.append(FAIL)
        result.append("label and data fields mismatch")
        return result
    if len(chart_data['legend'][0]) != len(chart_data['data']):
        result.append(FAIL)
        result.append("legend and data fields mismatch")
        return result
    result.append(PASS)
    return result

