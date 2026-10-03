## Process this file with automake to generate Makefile.in
#
#   Copyright (C) 2012-2018 Free Software Foundation, Inc.
#
# This file is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; see the file COPYING3.  If not see
# <http://www.gnu.org/licenses/>.
#

AUTOMAKE_OPTIONS = 1.9 cygnus

PROTOS = archive.p archures.p bfd.p \
	 core.p format.p \
	bfdio.p bfdwin.p \
	libbfd.p opncls.p reloc.p \
	section.p syms.p targets.p  \
	format.p  core.p init.p

IPROTOS = cache.ip libbfd.ip reloc.ip init.ip archures.ip coffcode.ip

# SRCDOC, SRCPROT, SRCIPROT only used to sidestep Sun Make bug in interaction 
# between VPATH and suffix rules.  If you use GNU Make, perhaps other Makes,
# you don't need these three:
SRCDOC = $(srcdir)/../aoutx.h  $(srcdir)/../archive.c \
	$(srcdir)/../archures.c $(srcdir)/../bfd.c \
	$(srcdir)/../bfdio.c $(srcdir)/../bfdwin.c \
	$(srcdir)/../cache.c $(srcdir)/../coffcode.h \
	$(srcdir)/../corefile.c $(srcdir)/../elf.c \
	$(srcdir)/../elfcode.h  $(srcdir)/../format.c \
	$(srcdir)/../libbfd.c $(srcdir)/../opncls.c \
	$(srcdir)/../reloc.c  $(srcdir)/../section.c \
	$(srcdir)/../syms.c  $(srcdir)/../targets.c \
	$(srcdir)/../hash.c $(srcdir)/../linker.c \
	$(srcdir)/../mmo.c

SRCPROT = $(srcdir)/../archive.c $(srcdir)/../archures.c \
	$(srcdir)/../bfd.c $(srcdir)/../coffcode.h $(srcdir)/../corefile.c \
	$(srcdir)/../format.c $(srcdir)/../libbfd.c \
	$(srcdir)/../bfdio.c $(srcdir)/../bfdwin.c \
	$(srcdir)/../opncls.c $(srcdir)/../reloc.c \
	$(srcdir)/../section.c $(srcdir)/../syms.c \
	$(srcdir)/../targets.c $(srcdir)/../init.c

SRCIPROT = $(srcdir)/../cache.c $(srcdir)/../libbfd.c \
	$(srcdir)/../bfdio.c $(srcdir)/../bfdwin.c \
	$(srcdir)/../reloc.c $(srcdir)/../cpu-h8300.c \
	$(srcdir)/../cpu-i960.c $(srcdir)/../archures.c \
	$(srcdir)/../init.c

MKDOC = chew$(EXEEXT_FOR_BUILD)

AM_CPPFLAGS = -I.. -I$(srcdir)/.. -I$(srcdir)/../../include \
	-I$(srcdir)/../../intl -I../../intl

$(MKDOC): chew.stamp ; @true
chew.stamp: $(srcdir)/chew.c
	$(CC_FOR_BUILD) -o chw$$$$$(EXEEXT_FOR_BUILD) $(CFLAGS_FOR_BUILD) \
	  $(LDFLAGS_FOR_BUILD) $(H_CFLAGS) $(AM_CPPFLAGS) $(srcdir)/chew.c; \
	$(SHELL) $(srcdir)/../../move-if-change \
	  chw$$$$$(EXEEXT_FOR_BUILD) $(MKDOC); \
	touch $@

protos: libbfd.h libcoff.h bfd.h

LIBBFD_H_DEP = \
	$(srcdir)/../libbfd-in.h	\
	$(srcdir)/../libbfd.c		\
	$(srcdir)/../bfdio.c		\
	$(srcdir)/../bfdwin.c		\
	$(srcdir)/../cache.c		\
	$(srcdir)/../reloc.c		\
	$(srcdir)/../archures.c		\
	$(srcdir)/../linker.c		\
	$(srcdir)/header.sed		\
	$(srcdir)/proto.str		\
	$(MKDOC)

libbfd.h: $(LIBBFD_H_DEP)
	echo "$(LIBBFD_H_DEP)" | sed -f $(srcdir)/header.sed > $@
	for file in $(LIBBFD_H_DEP); do \
	  case $$file in \
	    *-in.h) cat $$file >> $@ ;; \
	    */header.sed) break ;; \
	    *)	echo $$file | sed -e 's,.*/,,' -e 's,^,/* Extracted from ,' \
				-e 's,$$,.  */,' >> $@ ; \
		./$(MKDOC) -i -f $(srcdir)/proto.str < $$file >> $@ ;; \
	  esac; \
	done
	echo "#ifdef __cplusplus" >> $@
	echo "}" >> $@
	echo "#endif" >> $@

LIBCOFF_H_DEP = \
	$(srcdir)/../libcoff-in.h	\
	$(srcdir)/../coffcode.h		\
	$(srcdir)/header.sed		\
	$(srcdir)/proto.str		\
	$(MKDOC)

libcoff.h: $(LIBCOFF_H_DEP)
	echo "$(LIBCOFF_H_DEP)" | sed -f $(srcdir)/header.sed > $@
	for file in $(LIBCOFF_H_DEP); do \
	  case $$file in \
	    *-in.h) cat $$file >> $@ ;; \
	    */header.sed) break ;; \
	    *)	echo $$file | sed -e 's,.*/,,' -e 's,^,/* Extracted from ,' \
				-e 's,$$,.  */,' >> $@ ; \
		./$(MKDOC) -i -f $(srcdir)/proto.str < $$file >> $@ ;; \
	  esac; \
	done
	echo "#ifdef __cplusplus" >> $@
	echo "}" >> $@
	echo "#endif" >> $@

BFD_H_DEP = \
	$(srcdir)/../bfd-in.h 		\
	$(srcdir)/../init.c 		\
	$(srcdir)/../opncls.c 		\
	$(srcdir)/../libbfd.c 		\
	$(srcdir)/../bfdio.c		\
	$(srcdir)/../bfdwin.c		\
	$(srcdir)/../section.c 		\
	$(srcdir)/../archures.c		\
	$(srcdir)/../reloc.c		\
	$(srcdir)/../syms.c		\
	$(srcdir)/../bfd.c		\
	$(srcdir)/../archive.c		\
	$(srcdir)/../corefile.c		\
	$(srcdir)/../targets.c		\
	$(srcdir)/../format.c		\
	$(srcdir)/../linker.c		\
	$(srcdir)/../simple.c		\
	$(srcdir)/../compress.c		\
	$(srcdir)/header.sed		\
	$(srcdir)/proto.str		\
	$(srcdir)/../version.h		\
	$(MKDOC)

bfd.h: $(BFD_H_DEP)
	echo "$(BFD_H_DEP)" | sed -f $(srcdir)/header.sed > $@
	for file in $(BFD_H_DEP); do \
	  case $$file in \
	    *-in.h) cat $$file >> $@ ;; \
	    */header.sed) break ;; \
	    *)	echo $$file | sed -e 's,.*/,,' -e 's,^,/* Extracted from ,' \
				-e 's,$$,.  */,' >> $@ ; \
		./$(MKDOC) -f $(srcdir)/proto.str < $$file >> $@ ;; \
	  esac; \
	done
	echo "#ifdef __cplusplus" >> $@
	echo "}" >> $@
	echo "#endif" >> $@
	echo "#endif" >> $@

MOSTLYCLEANFILES = $(MKDOC) *.o *.stamp

CLEANFILES = *.p *.ip

DISTCLEANFILES = bfd.?? bfd.??? bfd.h libbfd.h libcoff.h texput.log
