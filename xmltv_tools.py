#!/usr/bin/env python2
# -*- coding: utf-8 -*-

 """
    SYNOPSIS

    xmltv_tools is a python script to manipulate xmltv listings
    It can be found here:

         https://github.com/tvgrabbers/xmltvtools/

    USAGE

    Check the web site above and/or run script with --help and start from there

    REQUIREMENTS

    * Python 2.6 or 2.7

    QUESTIONS

    Questions (and patches) are welcome at:
    https://github.com/tvgrabbers/xmltvtools/issues

    LICENSE

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import sys, codecs, locale, argparse
import io, os, os.path, time, datetime
from xml.etree import cElementTree as ET
try:
    unichr(42)
except NameError:
    unichr = chr    # Python 3

# check Python version
if sys.version_info[:2] < (2,6):
    sys.stderr.write("xmltv_tools requires Pyton 2.6 or higher\n")
    sys.exit(2)

elif sys.version_info[:2] >= (3,0):
    sys.stderr.write("xmltv_tools does not support Pyton 3 or higher.\nExpect errors while we proceed\n")

def log(message, log_level = 1, log_target = 3):
    # Prints a warning to stderr.
    def now():
         return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z') + ': '

    try:
        # If config is not yet available
        if (config == None) and (log_target & 1):
            sys.stderr.write('Error writing to log. Not (yet) available?\n')
            sys.stderr.write(message.encode("utf-8"))
            return

        # Log to the screen
        elif log_level == 0 or ((not config.quiet) and (log_level & config.log_level) and (log_target & 1)):
            sys.stdout.write(message.encode("utf-8"))

        # Log to the log-file
        if (log_level == 0 or ((log_level & config.log_level) and (log_target & 2))) and config.log_output != None:
           sys.stderr.write(now() + unicode(message.replace('\n','') + '\n'))

    except:
        print 'An error ocured while logging!'
        sys.stderr.write(now() + 'An error: "%s" ocured while logging!\n' % sys.exc_info()[1])

# end log()

class Configure:
    def __init__(self):
        """
        DEFAULT OPTIONS - Edit if you know what you are doing
        """
        # Version info as returned by the version function
        self.name ='xmltv_tools'
        self.major = 0
        self.minor = 1
        self.patch = 1
        self.patchdate = u'20150513'
        self.alfa = False
        self.beta = True

        self.file_encoding = 'utf-8'
        self.log_output = None
        self.log_file = ''
        self.log_level = 1
        self.quiet = False
        self.output = None
        self.input = None
        self.tag_order = [{'name': 'programme', 'ident': 2, 'values':{
                                    0: 'title',
                                    1: 'sub-title',
                                    2: 'desc',
                                    3: 'credits',
                                    4: 'date',
                                    5: 'category',
                                    6: 'language',
                                    7: 'orig-language',
                                    8: 'length',
                                    9: 'icon',
                                    10: 'url',
                                    11: 'country',
                                    12: 'episode-num',
                                    13: 'video',
                                    14: 'audio',
                                    15: 'previously-shown',
                                    16: 'mremiere',
                                    17: 'last-chance',
                                    18: 'new',
                                    19: 'subtitles',
                                    20: 'rating',
                                    21: 'start-rating',
                                    22: 'review'}}]
        self.attrib_order = [{'name': 'programme', 'ident': 2, 'values':{
                                    0: 'start',
                                    1: 'stop',
                                    2: 'pdc-start',
                                    3: 'vps-start',
                                    4: 'showview',
                                    5: 'videoplus',
                                    6: 'channel',
                                    7: 'clumpidx'}},
                                    {'name': 'icon', 'ident': 4, 'values':{
                                    0: 'src',
                                    1: 'width',
                                    2: 'height'}}]
    # end Init()

    def version(self, as_string = False):
        """
        return tuple or string with version info
        """
        if as_string and self.alfa:
            return u'%s (Version: %s.%s.%s-p%s-alpha)' % (self.name, self.major, self.minor, self.patch, self.patchdate)

        elif as_string and self.beta:
            return u'%s (Version: %s.%s.%s-p%s-beta)' % (self.name, self.major, self.minor, self.patch, self.patchdate)

        elif as_string:
            return u'%s (Version: %s.%s.%s-p%s)' % (self.name, self.major, self.minor, self.patch, self.patchdate)

        else:
            return (self.name, self.major, self.minor, self.patch, self.patchdate, self.beta, self.alfa)

    # end version()

    def save_oldfile(self, file):
        """ save the old file to .old if it exists """
        try:
            os.rename(file, file + '.old')

        except Exception as e:
            pass

    # end save_old()

    def open_file(self, file_name, mode = 'rb', encoding = None):
        """ Open a file and return a file handler if success """
        if encoding == None:
            encoding = self.file_encoding

        try:
            if 'b' in mode:
                file_handler =  io.open(file_name, mode = mode)
            else:
                file_handler =  io.open(file_name, mode = mode, encoding = encoding)

        except IOError as e:
            if e.errno == 2:
                log('File: \"%s\" not found.\n' % file_name)
            else:
                log('File: \"%s\": %s.\n' % (file_name, e.strerror))
            return None

        return file_handler

    # end open_file ()

    def get_line(self, file, byteline, isremark = False, encoding = None):
        """
        Check line encoding and if valid return the line
        If isremark is True or False only remarks or non-remarks are returned.
        If None all are returned
        """
        if encoding == None:
            encoding = self.file_encoding

        try:
            line = byteline.decode(encoding)
            line = line.lstrip()
            line = line.replace('\n','')
            if isremark == None:
                return line

            if len(line) == 0:
                return False

            if isremark and line[0:1] == '#':
                return line

            if not isremark and not line[0:1] == '#':
                return line

        except UnicodeError:
            log('%s is not encoded in %s.\n' % (file.name, encoding))

        return False

    # end get_line()

    def read_commandline(self):
        """Initiate argparser and read the commandline"""
        v=self.version()
        self.description = 'The Netherlands: v%s.%s.%s\n' % (v[1], v[2], v[3]) + \
                        '  On the given channels, remove all HD tags or add one to all programs.\n' + \
                        '  Optionally adding as a new listing with \'-sd\' or \'-hd\' added to the xmltvID.\n'

        parser = argparse.ArgumentParser(description = self.description, formatter_class=argparse.RawTextHelpFormatter)

        parser.add_argument('-v', '--version', action = 'store_true', default = False, dest = 'version',
                        help = 'display version')

        parser.add_argument('-d', '--description', action = 'store_true', default = False, dest = 'description',
                        help = 'prints the above short description')

        parser.add_argument('-q', '--quiet', action = 'store_true', default = False, dest = 'quiet',
                        help = 'suppress all output.')

        parser.add_argument('-L', '--log-level', type = int, default = 1, dest = 'log_level',
                        metavar = '<level>',
                        help = 'Set the loglevel [0-2] default = 1')

        parser.add_argument('-I', '--input', type = str, default = None, dest = 'input_file',
                        metavar = '<file>',
                        help = 'file to read from')

        parser.add_argument('-x', '--id-list', nargs = '*', dest = 'id_list',
                        metavar = '<xmltvID>',
                        help = 'The xmltvIDs to process.')

        parser.add_argument('-O', '--output', type = str, default = None, dest = 'output_file',
                        metavar = '<file>',
                        help = 'file or directory where to send the output.\n' + \
                                    'Defaults to \'xmltv.out\' in the input directory. If just\n' + \
                                    'a filename is given, the current directory is assumed.')

        parser.add_argument('-r', '--remove-HD-tags', action = 'store_true', default = None, dest = 'remove_hd_tags',
                        help = 'remove the HD tags from given channels <default action>')

        parser.add_argument('-t', '--add-HD-tags', action = 'store_false', default = None, dest = 'remove_hd_tags',
                        help = 'add a HD tag to all programs from given channels')

        parser.add_argument('-n', '--add-new-id', action = 'store_true', default = False, dest = 'add_new_id',
                        help = 'Preserve the old listing and add the processed channel\n' + \
                                    'with a new id, adding \'-sd\' or \'-hd\' to the old xmltvID')

        # Handle the sys.exit(0) exception on --help more gracefull
        try:
            self.args = parser.parse_args()

        except:
            return(0)

        self.quiet = self.args.quiet
        if self.args.version:
            print("The Netherlands: %s" % self.version(True))
            return(0)

        if self.args.description:
            print self.description
            return(0)

        if self.args.input_file == None:
            print 'Please give an xmltv file to process\n'
            return(1)

        else:
            self.input_file =  os.path.realpath(self.args.input_file)

            if not os.access(self.input_file, os.R_OK):
                log('The xmltv file: %s does not exist or is not readable\n' % (self.input_file))
                return(1)

            self.log_file = '%s.log' % self.input_file
            try:
                self.save_oldfile(self.log_file)
                self.log_output = self.open_file(self.log_file, mode = 'a')
                if self.log_output != None:
                    sys.stderr = self.log_output

                else:
                    log(u'Cannot write to logfile: %s\n' % self.log_file, 0)
                    return(2)

                log(u"The Netherlands: %s\n" % config.version(True))
                self.input = self.open_file(self.input_file)

            except Exception:
                log(u'Cannot write to logfile: %s\n' % self.log_file, 0)
                return(2)


        if self.args.id_list == None or len(self.args.id_list) == 0:
            log(u'Please give one or more xmltvID\'s to process\n', 0)
            return(1)

        if self.args.output_file == None:
            self.output_file = u'%s/xmltv.out' % os.path.dirname(self.input_file)

        elif self.args.output_file[-1] == '/' or  self.args.output_file[-1] == '.' or os.path.isdir(self.args.output_file):
               self.output_file = os.path.realpath(u'%s/xmltv.out' % self.args.output_file)

        else:
            self.output_file = os.path.realpath(self.args.output_file)

        try:
            out_dir = os.path.dirname(self.output_file)
            if (out_dir != '') and not os.path.exists(out_dir):
                log(u'Creating %s directory,\n' % out_dir)
                os.mkdir(out_dir)

            if not os.access(out_dir, os.W_OK):
                log(u'The output directory: %s is not writable\n' % (out_dir), 0)
                return(1)

            if os.access(self.output_file, os.F_OK) and not os.access(self.output_file, os.W_OK):
                log(u'%s exists and is not writable\n' % (self.output_file), 0)
                return(1)

            self.output = self.open_file(self.output_file, mode = 'w')

        except:
            log(u'Error creating the output directory and or file: %s\n' % (self.output_file), 0)
            return(1)

        log(u'using %s for the output\n' % self.output_file)
        return

    # end read_commandline()

    def close(self):

        # close everything neatly
        try:
            if self.input != None:
                self.input.close()

            if self.output != None:
                self.output.close()

            if self.log_output != None:
                self.log_output.close()

        except:
            pass

    # end close()

# end Configure
config = Configure()

class Process_XML():
    def __init__(self):
        self.channels = []
        self.chan_list = []
        self.programs = {}
        self.out_string = u''
        self.chan_out_string = u''
        self.prog_out_string = u''
    # end Init()

    def read_input(self):
        try:
            self.output_header = u''
            for byteline in config.input.readlines():
                line = config.get_line(config.input, byteline)
                self.output_header += u'%s\n' % line
                if line[0:3] == '<tv':
                    break

            self.input_string = u''
            config.input.seek(0,0)
            for byteline in config.input.readlines():
                line = config.get_line(config.input, byteline)
                self.input_string += u'%s\n' % line

            self.input_string += u''
            self.et_object = ET.fromstring(self.input_string.encode('utf-8'))

        except:
            log(u'error: %s parsing %s\n' % (sys.exc_info()[1], config.input), 0)
            return 2

    # end read_input()

    def process_xml(self):
        """
        Every tag becomes a dict with 4 elements:
            attribs: with a dict of attrib names and values
            text: the text behind the starttag
            tail: the text behind the endtag
            tags: a list of dicts with 2 elements:
                tag: the name
                value: a dict like this
        """
        def read_tag(tag):
            sdict = {}
            sdict['text'] = None if tag.text == None else tag.text.strip()
            sdict['tail'] = None if tag.tail == None else tag.tail.strip()
            sdict['attribs'] ={}
            sdict['tags'] =[]
            for a, t in tag.attrib.items():
                sdict['attribs'][a] = t

            for t in tag.findall('./'):
                sdict['tags'].append({'tag': t.tag, 'value': read_tag(t)})

            return sdict

        for c in self.et_object.findall('channel[@id]'):
            c_id = c.get('id')
            if c_id == None or c_id == '':
                continue

            self.chan_list.append(c_id)
            self.channels.append(read_tag(c))
            self.programs[c_id] = []

        for p in self.et_object.findall('programme[@channel]'):
            c_id = p.get('channel')
            if c_id == None or c_id == '':
                continue

            if not c_id in self.programs.keys():
                self.programs[c_id] = []

            self.programs[c_id].append(read_tag(p))

    # end process_xml()

    def check_chanids(self):
        cancel_processing = False
        for chanid in config.args.id_list:
            if not chanid in self.chan_list:
                log(u'The requested xmltvID: "%s" is not found in the input file\n' % (chanid), 0)
                cancel_processing = True
            if config.args.add_new_id:
                if config.args.remove_hd_tags == True and '%s-sd' % (chanid) in self.chan_list:
                    log(u'I can not add the xmltvID: "%s-sd". It already exists in the input file.\n' % (chanid), 0)
                    cancel_processing = True

                if config.args.remove_hd_tags == False and '%s-hd' % (chanid) in self.chan_list:
                    log(u'I can not add the xmltvID: "%s-hd". It already exists in the input file.\n' % (chanid), 0)
                    cancel_processing = True

        if cancel_processing:
            log(u'Canceling the processing of: %s\n' % (config.input_file), 0)
            return False

        return True

    # end add_hd_tags()

    def process_requests(self):
        for channel in self.channels[:]:
            chanid = channel['attribs']['id']
            if chanid in config.args.id_list:
                programs = self.programs[chanid]
                if config.args.add_new_id:
                    # preserve the old listings
                    log(u'Preserving the old listing for %s\n' % (chanid))
                    self.create_output(chanid)

                if config.args.remove_hd_tags == True:
                    log (u'Removing HDTV tags from %s\n' % (chanid))
                    self.remove_hd_tags(chanid, programs)

                    if config.args.add_new_id:
                        chanid = u'%s-sd' % (chanid)
                        channel['attribs']['id'] = chanid

                    log(u'Creating the new listing for %s\n' % (chanid))
                    self.create_output(chanid)

                elif config.args.remove_hd_tags == False:
                    log (u'Adding HDTV tags to %s\n' % (chanid))
                    self.add_hd_tags(chanid, programs)

                    if config.args.add_new_id:
                        chanid = u'%s-hd' % (chanid)
                        channel['attribs']['id'] = chanid

                    log(u'Creating the new listing for %s\n' % (chanid))
                    self.create_output(chanid)

                elif config.args.remove_hd_tags == None:
                    continue

            else:
                log(u'Preserving the old listing for %s\n' % (chanid))
                self.create_output(chanid)

    # end process_requests()

    def remove_hd_tags(self, chanid, programs):
        prog_list = []
        t_count = 0
        for p in programs[:]:
            if config.args.add_new_id:
                p['attribs']['channel'] = u'%s-sd' % (chanid)

            for t in range(len(p['tags'])):
                if p['tags'][t]['tag'] == 'title':
                    ptitle = p['tags'][t]['value']['text']

                if p['tags'][t]['tag'] == 'video':
                    for v in p['tags'][t]['value']['tags']:
                        if v['tag'] == 'quality' and v['value']['text'].lower() == 'hdtv':
                            log(u'Removed HDTV tag from %s on xmltvID %s\n' % (ptitle, chanid), 2)
                            t_count += 1
                            if len(p['tags'][t]['value']['tags']) == 1:
                                p['tags'].pop(t)

                            else:
                                p['tags'][t]['value']['tags'] .remove(v)

                            break

                    prog_list.append(p)
                    break

            else:
                prog_list.append(p)

        log (u'%s HDTV tags removed from %s\n' % (t_count, chanid))
        if config.args.add_new_id:
            self.programs[u'%s-sd' % (chanid)] = prog_list
            #~ del self.programs[chanid]

        else:
            self.programs[chanid] = prog_list

    # end remove_hd_tags()

    def add_hd_tags(self, chanid, programs):
        prog_list = []
        t_count = 0
        for p in programs[:]:
            if config.args.add_new_id:
                p['attribs']['channel'] = u'%s-hd' % (chanid)

            for t in range(len(p['tags'])):
                if p['tags'][t]['tag'] == 'title':
                    ptitle = p['tags'][t]['value']['text']

                if p['tags'][t]['tag'] == 'video':
                    for v in p['tags'][t]['value']['tags']:
                        if v['tag'] == 'quality' and v['value']['text'].lower() == 'hdtv':
                            prog_list.append(p)
                            break

                    else:
                        log(u'Added HDTV tag to %s on xmltvID %s\n' % (ptitle, chanid), 2)
                        t_count += 1
                        p['tags'][t]['value']['tags'].append({'tag': 'quality',
                                                                                              'value':{'attribs':{},
                                                                                                               'text':'HDTV',
                                                                                                               'tail':'',
                                                                                                               'tags':[]}})

                        prog_list.append(p)
                        break

            else:
                log(u'Added HDTV tag to %s on xmltvID %s\n' % (ptitle, chanid), 2)
                t_count += 1
                p['tags'].append({'tag': 'video',
                                                 'value':{'attribs':{},
                                                                  'text':'',
                                                                  'tail':'',
                                                                  'tags':[{'tag': 'quality',
                                                                                   'value':{'attribs':{},
                                                                                                    'text':'HDTV',
                                                                                                    'tail':'',
                                                                                                    'tags':[]}}]}})

                prog_list.append(p)

        log (u'%s HDTV tags added to %s\n' % (t_count, chanid))
        if config.args.add_new_id:
            self.programs[u'%s-hd' % (chanid)] = prog_list
            del self.programs[chanid]

        else:
            self.programs[chanid] = prog_list

    # end add_hd_tags()

    def create_output(self, chanid = None):
        def create_tag(name, sdict, ident = 0):
            out_str = u'%s<%s' % ( ''.rjust(ident), name)
            # Put some of the attribute in order
            processed = []
            for o in config.attrib_order:
                if ident == o['ident'] and name == o['name']:
                    for i in range(len(o['values'])):
                        processed.append(o['values'][i])
                        for a, v in sdict['attribs'].items():
                            if a == o['values'][i]:
                                out_str += u' %s="%s"' % (a, v)
                                break

                    break

            for a, v in sdict['attribs'].items():
                if not a in processed:
                    out_str += u' %s="%s"' % (a, v)

            # Text is None so close the tag immidiately and return
            if  sdict['text'] == None:
                return u'%s/>%s\n' % (out_str, sdict['tail'])

            # There are no children so append any text a closing tag, a possible tail and return
            elif len(sdict['tags']) == 0:
                return u'%s>%s</%s>%s\n' % (out_str, sdict['text'], name, sdict['tail'])

            # We finnish the start tag and add a possible text on a newline
            elif sdict['text'] == '':
                out_str += u'>\n'

            else:
                out_str += u'>\n%s%s\n' % (''.rjust(ident + 2), sdict['text'])

            # We have to put some child tags in the right order
            processed = []
            for o in config.tag_order:
                if ident == o['ident'] and name == o['name']:
                    for i in range(len(o['values'])):
                        processed.append(o['values'][i])
                        #~ for t in range(len(sdict['tags'])-1, -1, -1):
                           #~ if sdict['tags'][t]['tag'] == o['values'][i]:
                                #~ out_str += create_tag(sdict['tags'][t]['tag'], sdict['tags'][t]['value'], ident + 2)
                        for t in sdict['tags']:
                           if t['tag'] == o['values'][i]:
                                out_str += create_tag(t['tag'], t['value'], ident + 2)
                                # With some the same tag can appear more than once so we don't break

                    break

            # for other child tags and any remaining ones
            for t in sdict['tags']:
                if not t['tag'] in processed:
                    out_str += create_tag(t['tag'], t['value'], ident + 2)

            # close the tag and return
            return u'%s%s</%s>\n' % (out_str, ''.rjust(ident), name)

        if chanid == None:
            self.out_string = self.output_header
            self.out_string += self.chan_out_string
            self.out_string += self.prog_out_string
            self.out_string += u'</tv>\n'

        else:
            for c in self.channels:
                if c['attribs']['id'] == chanid:
                    self.chan_out_string += create_tag(u'channel', c, 2)

            for p in self.programs[chanid]:
                self.prog_out_string += create_tag(u'programme', p, 2)


    # create_output()

# end process_xml_file()

def main():
    try:
        # Process the commandline etc
        x = config.read_commandline()
        if x != None:
            return(x)

        xml = Process_XML()
        # read in a xmltv file
        x = xml.read_input()
        if x != None:
            return(x)

        xml.process_xml()

        # Check if the requested xmltvID's are present and processable
        if not xml.check_chanids():
            return(1)

        # do any processing
        xml.process_requests()

        # create the new xmltv output
        xml.create_output()
        # and write it to file
        config.output.write(xml.out_string)

    except:
        err_obj = sys.exc_info()[2]
        log(u'\nAn unexpected error has occured at line: %s, %s: %s\n' %  (err_obj.tb_lineno, err_obj.tb_lasti, sys.exc_info()[1]), 0)

        while True:
            err_obj = err_obj.tb_next
            if err_obj == None:
                break

            log(u'                   tracing back to line: %s, %s\n' %  (err_obj.tb_lineno, err_obj.tb_lasti), 0)

        log(u'\nIf you want assistence, please attach your log file!\n     %s\n' % (config.log_file),0)
        return(99)

    # and return success
    return(0)
# end main()

# allow this to be a module
if __name__ == '__main__':
    x = main()
    config.close()
    sys.exit(x)
