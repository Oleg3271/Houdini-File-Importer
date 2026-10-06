import os
import re
import hou

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

def write_log(log):
    current_dir = os.getcwd()
    file_dir = os.path.join(current_dir, "log.txt")
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    message = f"{current_time}, Log: {log}\n"
    
    with open(file_dir, "a", encoding="utf-8") as file:
        file.write(message)
        
    return log

class BaseFormatHandler(ABC):
    @abstractmethod
    def import_file(self, parent_node: hou.Node, file_path: str, node_name: str) -> hou.Node:
        pass

class AlembicHandler(BaseFormatHandler):
    def import_file(self, parent_node: hou.Node, file_path: str, node_name: str) -> hou.Node:
        node = parent_node.createNode("alembic", f"abc_{node_name}")
        node.parm("fileName").set(file_path)
        
        return node
        
class USDHandler(BaseFormatHandler):
    def import_file(self, parent_node: hou.Node, file_path: str, node_name: str) -> hou.Node:
        node = parent_node.createNode("usdimport", f"usd_{node_name}")
        node.parm("filepath1").set(file_path)
        
        return node
        
class ObjHandler(BaseFormatHandler):
    def import_file(self, parent_node: hou.Node, file_path: str, node_name: str) -> hou.Node:
        node = parent_node.createNode("file", f"obj_{node_name}")
        node.parm("file").set(file_path)

FORMAT_REGISTRY = {
    ".abc": AlembicHandler(),
    ".usd": USDHandler(),
}

class StudioValidator:
    @staticmethod
    def validate_file(file_path: str) -> tuple[bool, str]:
        if not file_path:
            return False, "Path is empty."

        absolute_path = hou.text.expandString(file_path)

        if not os.path.exists(absolute_path):
            return False, f"File doesn't exist:\n{absolute_path}."

        if os.path.getsize(absolute_path) == 0:
            return False, "File is broken."

        file_lower = absolute_path.lower()
        has_valid_extension = any(file_lower.endswith(ext) for ext in FORMAT_REGISTRY.keys())
        
        if not has_valid_extension:
            allowed = ", ".join(FORMAT_REGISTRY.keys())
            
            write_log("Restricted: Attempt to import not allowed file.")
            
            return False, f"File is not suitable. Allowed formats: {allowed}."

        return True, ""

class cubic_importer:
    def __init__(self):
        self.validator = StudioValidator()

    def _sanitize_node_name(self, file_path: str) -> str:
        base_name = os.path.basename(file_path)
        
        for ext in FORMAT_REGISTRY.keys():
            if base_name.lower().endswith(ext):
                base_name = base_name[:-len(ext)]
                
                break
        
        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)

        if clean_name and clean_name[0].isdigit():
            clean_name = f"node_{clean_name}"
            
        return clean_name if clean_name else "cubic_imports"
        
    def run(self):
        try:
            pattern_str = " ".join([f"*{ext}" for ext in FORMAT_REGISTRY.keys()])

            file_path = hou.ui.selectFile(
                title="Cubic: File Import",
                pattern=pattern_str,
                chooser_mode=hou.fileChooserMode.Read
                )
            
            if not file_path:
                return
    
            is_valid, error_message = self.validator.validate_file(file_path)
                
            if not is_valid:
                hou.ui.displayMessage(error_message, severity=hou.severityType.Error)
                    
                return
    
            obj_context = hou.node("/obj")
            container = hou.node("/obj/cubic_imports")
                
            if not container:
                container = obj_context.createNode("geo", "file_imports")
                
            file_lower = file_path.lower()
            handler = None
                
            for ext, format_handler in FORMAT_REGISTRY.items():
                if file_lower.endswith(ext):
                    handler = format_handler
                    
                    break
    
            if not handler:
                raise ValueError("Critical Error: File was not found.")
        
            node_name = self._sanitize_node_name(file_path)
        
            new_node = handler.import_file(container, file_path, node_name)
                    
            obj_context.layoutChildren()
            
            write_log("File was successfully created.")
            
        except hou.Error as e:
                write_log(f"Houdini Error: {e}")
                
                hou.ui.displayMessage(f"Houdini API Error. Check logs for more information.", severity=hou.severityType.Error)
                
        except Exception as e:
                write_log(f"Houdini Error: {e}")
                
                hou.ui.displayMessage(f"Unexpected Error: Check logs for more information.", severity=hou.severityType.Error)
                
tool = cubic_importer()
tool.run()