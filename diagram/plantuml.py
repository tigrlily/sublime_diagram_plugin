from __future__ import absolute_import
from .base import BaseDiagram
from .base import BaseProcessor
from subprocess import Popen as execute, PIPE, STDOUT, call
from os.path import abspath, dirname, exists, join, split, splitext, isabs, isdir
from os import makedirs
import os
from tempfile import NamedTemporaryFile, gettempdir
from platform import system
from sublime import Region, status_message, error_message
from re import compile as re_compile, sub as re_sub
#from shlex import split as shlex_split

IS_MSWINDOWS = (system() == 'Windows')
CREATE_NO_WINDOW = 0x08000000  # See MSDN, http://goo.gl/l4OKNe
EXTRA_CALL_ARGS = {'creationflags': CREATE_NO_WINDOW} if IS_MSWINDOWS else {}
INLINE_TITLE = re_compile('(?i)^\\s*title\\s+(?P<diagramTitle>.+?)\\s*$')
MTLINE_TITLE = re_compile('(?i)^\\s*title\\s*$')
#INCLUDE = re_compile('^\\s*!include\\s+(?P<path>.+)$')

class PlantUMLDiagram(BaseDiagram):
    def __init__(self, processor, sourceFile, text):
        super(PlantUMLDiagram, self).__init__(processor, sourceFile, text)
        #self.import_include()

    def generate(self, index, isPreview):

        outputFormat = self.proc.FORMAT
        startDir = split(self.sourceFile)[0]
        fileName = self.get_file_name(index)+'.'+outputFormat

        status_message("Generating Diagram: "+fileName)

        if isPreview:
            outputfile = os.sep.join([gettempdir(), 'TempDiagrams', fileName])
        else:
            outputfile = os.sep.join([startDir, fileName])
        print(outputfile)

        newPath = split(outputfile)[0]
        if not exists(newPath):
            print(newPath+' not exists, creating...')
            makedirs(newPath)
        else:
            if not isdir(newPath):
                error_message(
                    'The path is already exists, and it''s not a folder.\\n'+
                    newPath+'\\n'+
                    'Please remove or rename it before you generate diagrams.'
                    )
                return
        self.file = open(outputfile,"w")

        # cmd='java -Dplantuml.include.path="%s" -jar "%s" -pipe -t%s' % (startDir,self.proc.plantuml_jar_path, outputFormat)
        # command=shlex_split(cmd)
        command = [
            'java',
            '-Dplantuml.include.path=%s' % startDir,
            '-jar',
            self.proc.plantuml_jar_path,
            '-pipe',
            '-t'+outputFormat
        ]

        charset = self.proc.CHARSET
        if charset:
            pass
        else:
            charset = 'UTF-8'
        #print('using charset: '+charset)
        command.append("-charset")
        command.append(charset)

        puml = execute(
            command,
            stdin=PIPE, stdout=self.file,
            **EXTRA_CALL_ARGS
        )
        puml.communicate(input=self.text.encode(charset))
        if puml.returncode != 0:
            print("Error Processing Diagram:")
            print(self.text)
            return
        else:
            return self.file
    # def import_include(self):
    #     for line in self.text.splitlines():
    #         include_match = INCLUDE.match(line)
    #         if include_match:
    #             path = include_match.group('path')
    #             matchline = include_match.group(0)
    #             #print(include_match.group(0)+':'+path)
    #             #print(isabs(path))
    #             if not isabs(path):
    #                 startDir = split(self.sourceFile)[0]
    #                 path = join(startDir,path)
    #                 print(path)
    #             if not exists(path):
    #                 incText = ''
    #                 #print('file not exists')
    #                 print('Warning: include file not exists [' + path + ']')
    #             else:
    #                 f = open(path,encoding=self.proc.CHARSET)
    #                 incText = f.read()
    #                 print('Preprocessing: including [' + path + ']')
    #                 f.close()
    #             self.text = self.text.replace(matchline,incText)
    #             #print(self.text)
    def get_file_name(self, index):
        #add title or index suffix to file name
        fileName = splitext(split(self.sourceFile)[1])[0]
        newFileName=fileName
        dgTitle = ''
        findA = False
        for line in self.text.splitlines():
            title_match = INLINE_TITLE.match(line)
            if title_match:
                dgTitle = title_match.group('diagramTitle')
                break
            mt_title_match = MTLINE_TITLE.match(line)
            if findA:
                dgTitle = line
                break
            if mt_title_match:
                findA = True
        if (dgTitle!=''):
            dgTitle = self.deal_title(dgTitle)
        if (dgTitle == ''):
            if (index != 0):
                #index == 0 means only one diagrams in one file
                newFileName += '\\Diagram-' + str(index)
        else:
            if (dgTitle!=fileName):
                newFileName += '\\' + dgTitle
        return newFileName
    def deal_title(self, text):
        # print(text)
        dealers = [
            # trim and remove Creole in head
            ['\\s*[\\*#=\\|]*\\s*(.+?)\\s*$', '\\1'],
            # \t to space
            ['(?<!\\\\)\\\\t', ' '],
            # \\ to \
            ['\\\\\\\\', '\\\\'],
            # *=|
            ['\\|(\\s*[\\*#=\\|]*)?\\s*', ' '],
            # |$
            ['\\|\\s*$', ''],
            # \\text\\
            ['\\*{2}(.+)\\*{2}', '\\1'],
            # __text__
            ['_{2}(.+)_{2}', '\\1'],
            # //text//
            ['\\/{2}(.+)\\/{2}', '\\1'],
            # ""text""
            ['"{2}(.+)"{2}', '\\1'],
            # --text--
            ['-{2}(.+)-{2}', '\\1'],
            # ~~text~~
            ['~{2}(.+)~{2}', '\\1'],
            # remove invalid chrs
            ['[\\\\/:*?"<>|]',' ']
        ]
        for [fnd,repl] in dealers:
            # print(fnd+', '+repl)
            text = re_sub(fnd,repl,text)
        return text.strip()
class PlantUMLProcessor(BaseProcessor):
    DIAGRAM_CLASS = PlantUMLDiagram
    PLANTUML_VERSION = 8036
    PLANTUML_VERSION_STRING = 'PlantUML version %s' % PLANTUML_VERSION

    def load(self):
        self.find_plantuml_jar()

        if self.CHECK_ON_STARTUP:
            self.check_dependencies()
            self.check_plantuml_version()
            self.check_plantuml_functionality()

    def check_dependencies(self):
        has_java = call(
            ["java", "-version"],
            **EXTRA_CALL_ARGS
        )

        if has_java is not 0:
            raise Exception("can't find Java")

    def check_plantuml_functionality(self):
        puml = execute(
            [
                'java',
                '-jar',
                self.plantuml_jar_path,
                '-testdot'
            ],
            stdout=PIPE,
            stderr=STDOUT,
            **EXTRA_CALL_ARGS
        )

        (stdout, stderr) = puml.communicate()
        dot_output = str(stdout)

        print("PlantUML Smoke Check:")
        print(dot_output)

        if ('OK' not in dot_output) or ('Error' in dot_output):
            raise Exception('PlantUML does not appear functional')

    def find_plantuml_jar(self):
        self.plantuml_jar_file = 'plantuml.%s.jar' % (self.PLANTUML_VERSION,)
        self.plantuml_jar_path = None

        self.plantuml_jar_path = abspath(
            join(
                dirname(__file__),
                self.plantuml_jar_file
            )
        )
        if not exists(self.plantuml_jar_path):
            raise Exception("can't find " + self.plantuml_jar_file)
        #print("Detected %r" % (self.plantuml_jar_path,))

    def check_plantuml_version(self):
        puml = execute(
            [
                'java',
                '-jar',
                self.plantuml_jar_path,
                '-version'
            ],
            stdout=PIPE,
            stderr=STDOUT,
            **EXTRA_CALL_ARGS
        )

        (stdout, stderr) = puml.communicate()
        version_output = stdout

        print("Version Detection:")
        print(version_output)

        if not puml.returncode == 0:
            raise Exception("PlantUML returned an error code")
        if self.PLANTUML_VERSION_STRING not in str(version_output):
            raise Exception("error verifying PlantUML version")

    def extract_blocks(self, view):
		# If any Region is selected - trying find @start-@end blocks in selection, if faild then trying to convert it, 
        # otherwise converting all @start-@end blocks in view
        sel = view.sel()
        if sel[0].a == sel[0].b:
            pairs = (
                    (start, view.find('@end', start.begin()),)
                    for start in view.find_all('@start')
                )
            return (view.full_line(start.cover(end)) for start, end in pairs)
        else:
            selStart = sel[0].a if sel[0].a<sel[0].b else sel[0].b 
            pairs = (
                    (selStart+findStart, view.find('@end', selStart+findStart).b,)
                    for findStart in self.str_find_all(view.substr(sel[0]),'@start')
                )
            pairs=list(pairs)
            if len(pairs)>0:
                #if find @start-@end blocks in selection
                return (view.full_line(Region(start,end)) for start, end in pairs)
            else:
                return sel
            
    def str_find_all(self,str,find):
        finds=[]
        pos=str.find(find,0,)
        while pos>=0:
            finds+=[pos]
            pos=str.find(find,pos+1,)
        return finds


class PlantUMLDoucment():
    def find_Document_PDF(self):
        Document_PDF_file = 'PlantUML_Language_Reference_Guide.pdf'
        Document_PDF_path = None
        Document_PDF_path = abspath(
            join(
                dirname(__file__),
                Document_PDF_file
            )
        )
        if not exists(Document_PDF_path):
            raise Exception("can't find " + Document_PDF_file)
        #print("Detected %r" % (self.Document_PDF_path,))
        doc = open(Document_PDF_path,'rb')
        #file.close()
        return [doc]
