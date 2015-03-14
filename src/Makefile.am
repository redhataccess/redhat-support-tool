#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

include $(top_srcdir)/build/python.inc

MAINTAINERCLEANFILES = \
	$(srcdir)/Makefile.in \
	$(NULL)

CLEANFILES = $(bin_SCRIPTS)

EXTRA_DIST = __main__.py

SUBDIRS = redhat_support_tool

bin_SCRIPTS = redhat-support-tool

redhat-support-tool: __main__.py Makefile
	cp $(srcdir)/__main__.py redhat-support-tool
	chmod +x redhat-support-tool

all-local: \
	python-syntax-check \
	$(NULL)

clean-local: \
	python-clean \
	$(NULL)
