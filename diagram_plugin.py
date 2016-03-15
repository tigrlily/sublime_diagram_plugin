from sublime_plugin import TextCommand, WindowCommand
from sublime import error_message, version, Region
try:
    from .diagram import setup, process, document
except ValueError:
    from diagram import setup, process, document


# build command
class BuildDiagramsCommand(WindowCommand):
    def run(self):
        active_view = self.window.active_view()
        if active_view.is_dirty():
            # Save the file so that source and target file on the drive don't differ
            active_view.run_command("save")
            if active_view.is_dirty():
                return error_message("Build Diagrams:\n"
                                     "The file could not be saved correctly. "
                                     "The build was aborted")
        file_path = active_view.file_name()
        if not file_path:
            return error_message("Build Diagrams: \n"
                                 "File does not exist!")
        scope=active_view.scope_name(active_view.sel()[0].begin()).split(' ')[0]
        if scope != 'source.wsd':
            return error_message("Build Diagrams: \n"
                                 "Not a diagram file!")
        if not process(active_view, False):
            return error_message("No diagrams overlap selections.\n\n" \
                "Nothing to process.")

class PreviewDiagrams(TextCommand):
    def run(self, edit):
        #print("Processing diagrams in %r..." % self.view)
        self.selCurDiagram()
        if not process(self.view, True):
            error_message("No diagrams overlap selections.\n\n" \
                "Nothing to process.")

    def selCurDiagram(self):
        sel=self.view.sel()
        if(len(sel)==1):
            lines=self.view.lines(sel[0])
            if(len(lines)==1):
                #Run in condition of only one selection and contains only one line
                content = self.view.substr(Region(0, self.view.size()))
                begin = self.view.line(content.rfind("@start",0,lines[0].b)).a
                if begin == -1:
                    return
                end = self.view.line(content.find("@end",lines[0].a,self.view.size())).b
                if end == -1 or begin>end:
                    return
                target_region = Region(begin, end)
                self.view.sel().clear()
                self.view.sel().add(target_region)

    def isEnabled(self):
        return True

class PlantumlDocument(TextCommand):
    def run(self, edit):
        document()
    def isEnabled(self):
        return True 
        
if version()[0] == '2':
    setup()
else:
    def plugin_loaded():
        """Sublime Text 3 callback to do after-loading initialization"""
        try:
            setup()
        except Exception:
            error_message("Unable to load diagram plugin, check console "
                "for details.")
            raise
