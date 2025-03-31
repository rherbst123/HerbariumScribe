import re

def get_image_ref(image_filename):
        try:        
            mtch = re.search(r"(.+[/\\])?(.+(jpg)|(jpeg)|(png))", image_filename)
            image_source = mtch.group(1) or "local: " + mtch.group(0)
            image_name = mtch.group(2)
        except:
            image_name = image_filename
            image_source = "undefined"
            print(f"ERROR: current regex does not capture image_ref: {image_filename}")
        return image_name, image_source

f1 = "C:\\Users\\dancs\\OneDrive\\Documents\\GitHub\\HerbariumScribe\\llm_processing\\transcripts\\2023-12-18-1734\\C0268502F_p.jpg"
f1 = 'C0268502F_p.jpg'
image_name, image_source = get_image_ref(f1)
print(f"{image_name = }, {image_source = }")          