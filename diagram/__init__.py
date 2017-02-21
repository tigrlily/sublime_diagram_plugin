from __future__ import absolute_import
from .plantuml import PlantUMLProcessor, PlantUMLDoucment
from .sublime3 import Sublime3Viewer
from .quicklook import QuickLookViewer
from .preview import PreviewViewer
from .eog import EyeOfGnomeViewer
from .freedesktop_default import FreedesktopDefaultViewer
from .windows import WindowsDefaultViewer
from threading import Thread
from os.path import splitext, split
from sublime import error_message, message_dialog, status_message, load_settings
import sys

INITIALIZED = False
RELOAD_ON_SAVE = False
AVAILABLE_PROCESSORS = [PlantUMLProcessor]
AVAILABLE_VIEWERS = [
    Sublime3Viewer,
    WindowsDefaultViewer,
    QuickLookViewer,
    EyeOfGnomeViewer,
    PreviewViewer,
    FreedesktopDefaultViewer,
]
AVAILABLE_STARTERS = [
    WindowsDefaultViewer,
    EyeOfGnomeViewer,
    PreviewViewer,
    FreedesktopDefaultViewer,
]
ACTIVE_PROCESSORS = []
ACTIVE_VIEWER = None
ACTIVE_FILE_STARTER = None

SUBLIME_SETTINGS = None

def setup():
    global INITIALIZED
    global ACTIVE_PROCESSORS
    global ACTIVE_VIEWER
    global SUBLIME_SETTINGS
    global RELOAD_ON_SAVE

    ACTIVE_PROCESSORS = []
    ACTIVE_VIEWER = None
    
    if SUBLIME_SETTINGS == None:
        SUBLIME_SETTINGS = load_settings("Diagram.sublime-settings")
        SUBLIME_SETTINGS.add_on_change('',setup)
    #print("Viewer Setting: " + SUBLIME_SETTINGS.get("viewer"))

    for processor in AVAILABLE_PROCESSORS:
        try:
            #print("Loading processor class: %r" % processor)
            proc = processor()
            proc.CHARSET = SUBLIME_SETTINGS.get('charset')
            proc.FORMAT = SUBLIME_SETTINGS.get('format')
            proc.CHECK_ON_STARTUP = SUBLIME_SETTINGS.get('check_on_startup')
            proc.load()
            ACTIVE_PROCESSORS.append(proc)
            #print("Loaded (processor): %r" % proc)
        except Exception:
            print("Unable to load processor: %r" % processor)
            sys.excepthook(*sys.exc_info())
    if not ACTIVE_PROCESSORS:
        raise Exception('No working processors found!')

    if SUBLIME_SETTINGS.get('format').lower()!='png':
        if Sublime3Viewer in AVAILABLE_VIEWERS:
            AVAILABLE_VIEWERS.remove(Sublime3Viewer)
    else:
        if not (Sublime3Viewer in AVAILABLE_VIEWERS):
            AVAILABLE_VIEWERS.insert(0,Sublime3Viewer)
    for viewer in AVAILABLE_VIEWERS:
        if viewer.__name__.find(SUBLIME_SETTINGS.get("viewer")) != -1:
            try:
                #print("Loading viewer class from configuration: %r" % viewer)
                vwr = viewer()
                vwr.load()
                ACTIVE_VIEWER = vwr
                #print("Loaded viewer: %r" % vwr)
                break
            except Exception:
                print("Unable to load configured viewer, falling back to autodetection...")
                sys.excepthook(*sys.exc_info())

    if ACTIVE_VIEWER is None:
        for viewer in AVAILABLE_VIEWERS:
            #print("Trying Viewer " + viewer.__name__)
            try:
                #print("Loading viewer class: %r" % viewer)
                vwr = viewer()
                vwr.load()
                ACTIVE_VIEWER = vwr
                #print("Loaded viewer: %r" % vwr)
                break
            except Exception:
                print("Unable to load viewer: %r" % viewer)
                sys.excepthook(*sys.exc_info())
    if ACTIVE_VIEWER is None:
        raise Exception('No working viewers found!')

    INITIALIZED = True
    RELOAD_ON_SAVE = SUBLIME_SETTINGS.get('reload_on_save')
    print(RELOAD_ON_SAVE)
    #print("Processors: %r" % ACTIVE_PROCESSORS)
    #print("Viewer: %r" % ACTIVE_VIEWER)

def process(view,isPreview, isTriggerdByReload=False):

    # Ignore this request
    if isTriggerdByReload and not RELOAD_ON_SAVE:
        return True

    diagrams = []

    for processor in ACTIVE_PROCESSORS:
        blocks = []

        for block in processor.extract_blocks(view):
            add = False
            for sel in view.sel():
                if sel.intersects(block):
                    add = True
                    break
            else:  # if there are no selections, add all blocks
                add = True
            if add:
                blocks.append(view.substr(block))

        if blocks:
            diagrams.append((processor, blocks, ))

    if diagrams:
        sourceFile = view.file_name()
        if sourceFile is None:
            sourceFile = 'untitled.txt'
        sourceFile = splitext(sourceFile)[0] 
        t = Thread(target=render_and_view, args=(sourceFile, diagrams,isPreview,))
        t.daemon = True
        t.start()
        return True
    else:
        return False


def render_and_view(sourceFile, diagrams, isPreview):
    #print("Rendering %r" % diagrams)
    diagram_files = []

    for processor, blocks in diagrams:
        diagram_files.extend(processor.process(sourceFile, blocks, isPreview))

    if diagram_files:
        if isPreview:
            #print("%r viewing %r" % (ACTIVE_VIEWER, [d.name for d in diagram_files]))
            print("viewing %r" % ([d.name for d in diagram_files]))
            ACTIVE_VIEWER.view(diagram_files)
            status_message("")
        else:
            filelist = ([split(d.name)[1] for d in diagram_files])
            status_message("Generating Diagrams Finish")
    else:
        error_message("No diagrams generated...")

def document():
    global ACTIVE_FILE_STARTER

    if ACTIVE_FILE_STARTER is None:
        for viewer in AVAILABLE_STARTERS:
            #print("Trying Viewer " + viewer.__name__)
            try:
                #print("Loading file starter class: %r" % viewer)
                vwr = viewer()
                vwr.load()
                ACTIVE_FILE_STARTER = vwr
                print("Loaded file starter: %r" % vwr)
                break
            except Exception:
                print("Unable to load file starter: %r" % viewer)
                sys.excepthook(*sys.exc_info())            
        if ACTIVE_FILE_STARTER is None:
            raise Exception('No working file starter found!')
    ACTIVE_FILE_STARTER.view(PlantUMLDoucment().find_Document_PDF())
