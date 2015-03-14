# -*- coding: utf-8 -*-

#
# Copyright (c) 2012 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from redhat_support_tool.helpers.confighelper import _


class Constants(object):
    MAX_RULE = 79
    BOLD = '\033[1m'
    END = '\033[0m'
    TITLE = _("Title")
    ISSUE = _("Issue")
    ENV = _("Environment")
    URL = _('URL:')
    ID = _('ID:')
    COMMENT = _('Comment:')
    ABSTRACT = _('Abstract:')
    RESOLUTION = _("Resolution")
    ROOT_CAUSE = _("Root Cause")
    DIAG = _("Diagnostic Steps")
    ARTICLE = _("Article")
    CASE_DETAILS = _("Case Details")
    CASE_TYPE = _("Case Type:")
    CASE_SEVERITY = _('Severity:')
    CASE_STATUS = _('Status:')
    CASE_AID = _('Alternate ID:')
    CASE_PROD = _('Product:')
    CASE_VER = _('Version:')
    CASE_SLA = _('Support Level:')
    CASE_OWNER = _('Owner:')
    CASE_RHOWN = _('Red Hat Owner:')
    CASE_GRP = _('Group:')
    CASE_OPENED = _('Opened:')
    CASE_OPENEDBY = _('Opened By:')
    CASE_UPDATED = _('Last Updated:')
    CASE_UPDATEDBY = _('Last Updated By:')
    CASE_DESCRIPTION = _('Description')
    CASE_SUMMARY = _('Summary:')
    CASE_DISCUSSION = _('Case Discussion')
    CASE_CMT_AUTHOR = _('Author:')
    CASE_CMT_DATE = _('Date:')
    CASE_GET_ATTACH = _('Get Attachment')
    CASE_ADD_ATTACH = _('Add Attachment')
    CASE_ADD_COMMENT = _('Add Comment')
    CASE_RECOMMENDATIONS = _('Recommendations')
    CASE_REC_SOURCE = _('Source:')
    CASE_REC_LINKED = _('Handpicked Recommendation')
    CASE_REC_UNLINKED = _('Automatic Text Analysis')
    CASE_NUMBER = _('Case Number')
    CASE_MODIFY = _('Modify Case')
    CASE_MODIFY_TYPE = _('Modify Type')
    CASE_MODIFY_SEVERITY = _('Modify Severity')
    CASE_MODIFY_STATUS = _('Modify Status')
    CASE_MODIFY_AID = _('Modify Alternative-ID')
    CASE_MODIFY_PROD = _('Modify Product')
    CASE_MODIFY_VER = _('Modify Version')
    CASE_TYPE_ARY = _('Bug'), _('Feature'), _('Info'), _('Other')
    CASE_SEVERITY_ARY = _('1 (Urgent)'), _('2 (High)'), _('3 (Normal)'), \
                            _('4 (Low)')
    CASE_STATUS_ARY = _('Waiting on Red Hat'), _('Waiting on Customer'), \
                        _('Closed')
    ATTACH_CREATE_BY = _('Created By:')
    ATTACH_CREATE = _('Date:')
    ATTACH_FILE_NAME = _('File Name:')
    ATTACH_DESCRIPTION = _('Description:')
    ATTACH_LENGTH = _('Length:')
    UUID = _('UUID:')
    PRODUCT_NAME = _('Name')
    ENTITLEMENT_NAME = _('Name:')
    ENTITLEMENT_SERVICE_LEVEL = _('Service Level:')
    ENTITLEMENT_SLA = _('SLA:')
    ENTITLEMENT_SUPPORT_LEVEL = _('Support Level:')
    ENTITLEMENT_START_DATE = _('Start Date:')
    ENTITLEMENT_END_DATE = _('End Date:')
