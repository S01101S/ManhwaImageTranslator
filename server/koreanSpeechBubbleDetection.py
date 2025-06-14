import sys
import cv2
import pytesseract
import numpy as np
import base64
import json
from deep_translator import GoogleTranslator
import re


try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\Fujitsu\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'
except Exception as e:
    print(json.dumps({"status": "error", "message": f"Tesseract config error: {e}"}), file=sys.stderr)
    sys.exit(1)


def base64ToImage(base64String):
    if "," in base64String:
        base64String = base64String.split(",")[1]

    imageByte = base64.b64decode(base64String)

    return cv2.imdecode(np.frombuffer(imageByte, np.uint8), cv2.IMREAD_COLOR)


def translatedText(text):

    if not text:
        return ""
    
    if not text.strip():
        return ""
    
    try:
        return GoogleTranslator(source="ko", target="en").translate(text)
    
    except Exception as e:
        print(f"Translation Error: {e}", file=sys.stderr)
        return "[Translation Failed]"




def cleanUpOCRText(text):
    
    if not text:
        return ""
    
    lines = text.split('\n')
    cleanedLines = []


    for i in lines:
        i = re.sub(r"[^\w\s.,!?'\"-]", "", i)
        i = i.strip()
        lineSeparator = i.replace("...", ".").replace("-.", ".").replace("/", "").replace(",", "")

        wordsInLine = len(i.split())

        if wordsInLine >= 2 or len(i) > 3:

            if lineSeparator:
                cleanedLines.append(lineSeparator)

    cleanedText = " ".join(cleanedLines)
    cleanedText = cleanedText.replace("'", "")

    if cleanedText.endswith("소리"):
        cleanedText += "?"

    return cleanedText



def checkingSpeechBubbles(image):

    if image is None:
        return {"status": "error", "message": "Invalid image data."}
    

    greyImage = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, threshHold = cv2.threshold(greyImage, 225, 255, cv2.THRESH_BINARY)
    kernel = np.ones((5, 5), np.uint8)
    morphed = cv2.morphologyEx(threshHold, cv2.MORPH_CLOSE, kernel, iterations=2)
    numLabels, labels, stats, centroids = cv2.connectedComponentsWithStats(morphed, 4, cv2.CV_32S)

    detectionParameters = {"min_area": 4000, "min_aspect_ratio": 0.5, "max_aspect_ratio": 6.0, "min_extent": 0.3}
    
    speechBubbles = []
    approvedSpeechBubbles = []

    for i in range(1, numLabels):

        x, y, w, h, area = stats[i]

        if area < 2000:
            continue

        speechBubbles.append((x,y,w,h))

        aspectRatio = w / h if h > 0 else 0
        extent = float(area) / (w * h) if (w * h) > 0 else 0

        if area < detectionParameters["min_area"]:
            continue

        if not (detectionParameters["min_aspect_ratio"] < aspectRatio < detectionParameters["max_aspect_ratio"]):
            continue

        if extent < detectionParameters["min_extent"]:
            continue

        approvedSpeechBubbles.append((x,y,w,h))

    finalText = ""

    if approvedSpeechBubbles:

        approvedSpeechBubbles.sort(key=lambda r:r[1])
        extractedText = []

        for i in approvedSpeechBubbles:

            x, y, w, h = i

            padding = 10
            xPad, yPad = max(0, x - padding), max(0, y - padding)
            wPad, hPad = min(image.shape[1] - xPad, w + (padding * 2)), min(image.shape[0] - yPad, h + (padding * 2))

            croppedImage = greyImage[yPad:yPad + hPad, xPad:xPad + wPad]

            try:
                finalOCRImage = cv2.bitwise_not(croppedImage)
                text = pytesseract.image_to_string(finalOCRImage, lang='kor', config='--psm 6').strip()
                text = re.sub(r'\s{2,}','', text)
                if text:
                    extractedText.append(text)

            except Exception as e:
                print(f"OCR processing error: {e}", file=sys.stderr)

        if extractedText:
            finalText = "\n\n".join(extractedText)
        else:
            finalText = "\n\n".join("Found bubbles but OCR could not read the text inside the bubbles")

    finalText = finalText.replace("/", "").replace(",", "")

    cleanedFinalText = cleanUpOCRText(finalText)
    translatedFinalText = translatedText(cleanedFinalText)


    finalTextLineBreak = finalText.split('\n')
    cleanedFinalTextLines = []

    for i in finalTextLineBreak:

        i = re.sub(r"[^\w\s.,!?'\"-]", "", i)
        finalLineSeparator = i.strip().replace("...", ".").replace("-.", ".").replace("/", "").replace(",", "")

        wordsInFinalLine = len(i.split())

        if wordsInFinalLine >= 2 or len(i) > 3:
            if finalLineSeparator:
                cleanedFinalTextLines.append(finalLineSeparator)

    finalText = "\n".join(cleanedFinalTextLines)
    finalText = finalText.replace("'", "")

    
    
    return {"status": "success", "text": finalText, "translated_final_text": translatedFinalText}
   






if __name__ == "__main__":
    try:

        if len(sys.argv) > 1:
            image = cv2.imread(sys.argv[1])
            if image is None: raise FileNotFoundError(f"Cannot read image at {sys.argv[1]}")
        else:
            base64_input = sys.stdin.read()
            image = base64ToImage(base64_input)
        
        if image is not None:
            resultData = checkingSpeechBubbles(image)
         
            
            if len(sys.argv) > 1:
                finalTextResult = {"status": resultData["status"], "text": resultData["text"]}
                print(json.dumps(finalTextResult, indent=2, ensure_ascii=False))

                debugImage = image.copy()
            

                for x,y,w,h in resultData.get("considered_rects", []):
                    cv2.rectangle(debugImage, (x,y), (x+w, y+h), (255, 100, 100), 2)
                
      
                overlay = debugImage.copy()
                alpha = 0.4
                for x,y,w,h in resultData.get("rects", []):
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 255), -1)
                cv2.addWeighted(overlay, alpha, debugImage, 1 - alpha, 0, debugImage)

                h_disp, w_disp = debugImage.shape[:2]
                if h_disp > 900: debugImage = cv2.resize(debugImage, (int(w_disp*900/h_disp), 900))
                
                cv2.imshow('Debug (Blue=Considered, Yellow=Accepted)', debugImage)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            else:
                print(json.dumps(resultData))
       
        else:
            print(json.dumps({"status": "error", "message": "Failed to decode Base64 string."}))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)









