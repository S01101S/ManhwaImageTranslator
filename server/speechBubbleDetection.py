import sys
import cv2
import pytesseract
import numpy as np
import base64
import json
import os
import re
from spellchecker import SpellChecker


try:
    spell = SpellChecker()
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    USER_WORDS_PATH = os.path.join(SCRIPT_DIR, 'spellCheckerFile.txt')
    if os.path.exists(USER_WORDS_PATH):
        spell.word_frequency.load_text_file(USER_WORDS_PATH)
except Exception as e:
    print(json.dumps({"status": "error", "message": f"Spellchecker or user file error: {e}"}), file=sys.stderr)
    sys.exit(1)


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


def correctingOCRErrors(text):

    if not text.strip():
        return ""
    
    substitutions = {'0': ['O'], '1': ['I', 'T', 'L'], '2': ['Z'], '5': ['S'], '8': ['B']}
    words = text.split()
    correctedWords = []

    for word in words:
        


        hasDigit = any(char.isdigit() for char in word)
        hasAlpha = any(char.isalpha() for char in word)

        if hasDigit and hasAlpha:

            foundCorrection = False

            for num, letters in substitutions.items():
                if num in word:
                    for letter in letters:
                        candidate = word.replace(num, letter)
                        
                        if spell.known([candidate.lower()]):
                            correctedWords.append(candidate)
                            foundCorrection = True
                            break
                    
                    if foundCorrection:
                        break
            if not foundCorrection:
                correctedWords.append(word)
        else:
            correctedWords.append(word)

    
    sentence = " ".join(correctedWords)
    wordsForGeneralCheck = re.findall(r"[\w]+|[.,!?-]", sentence)
    misspelled = spell.unknown(wordsForGeneralCheck)

    finalSentence = []

    for word in wordsForGeneralCheck:
        
        if word.lower() in misspelled:
            correction = spell.correction(word)
            
            if correction is not None:
                finalSentence.append(correction)
            else:
                finalSentence.append(word)

        else:
            finalSentence.append(word)

    finalText = ""

    for i, word in enumerate(finalSentence):
        
        if i > 0 and word not in ".,!?-":
            finalText += " "
        
        finalText += word

    return finalText.strip()



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
                text = pytesseract.image_to_string(finalOCRImage, lang='eng', config='--psm 6').strip()
                if text:
                    extractedText.append(text)

            except Exception as e:
                print(f"OCR processing error: {e}", file=sys.stderr)

        if extractedText:
            finalText = "\n\n".join(extractedText)
        else:
            finalText = "\n\n".join("Found bubbles but OCR could not read the text inside the bubbles")
    
    finalCorrectedText = correctingOCRErrors(finalText)


    return{"status": "success", "text": finalCorrectedText, "approvedbubbles": approvedSpeechBubbles, "consideredbubbles": speechBubbles}



if __name__ == "__main__":

    try:

        if len(sys.argv) > 1:
            image = cv2.imread(sys.argv[1])
            if image is None:
                raise FileNotFoundError(f"Cannot read image at {sys.argv[1]}")
        
        else:
            base64Input = sys.stdin.read()
            image = base64ToImage(base64Input)

        if image is not None:
            resultImage = checkingSpeechBubbles(image)

            if len(sys.argv) > 1:
                final_text_result = {"status": resultImage["status"], "text": resultImage["text"]}
                print(json.dumps(final_text_result, indent=2, ensure_ascii=False))

                debug_image = image.copy()
                
              
                for x,y,w,h in resultImage.get("considered_rects", []):
                    cv2.rectangle(debug_image, (x,y), (x+w, y+h), (255, 100, 100), 2)
                
             
                overlay = debug_image.copy()
                alpha = 0.4
                for x,y,w,h in resultImage.get("rects", []):
                    cv2.rectangle(overlay, (x, y), (x + w, y + h), (0, 255, 255), -1)
                cv2.addWeighted(overlay, alpha, debug_image, 1 - alpha, 0, debug_image)

                h_disp, w_disp = debug_image.shape[:2]
                if h_disp > 900: debug_image = cv2.resize(debug_image, (int(w_disp*900/h_disp), 900))
                
                cv2.imshow('Debug (Blue=Considered, Yellow=Accepted)', debug_image)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            
            else:
                print(json.dumps({"status": resultImage["status"], "text": resultImage["text"]}))
        
        else:
            print(json.dumps({"status": "error", "message": "Failed to decode Base64 string."}))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}), file=sys.stderr)
        sys.exit(1)



