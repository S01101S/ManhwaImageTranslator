document.addEventListener('DOMContentLoaded', () => {

    const scanTextButton = document.getElementById('extract');
    const originalTextInput = document.getElementById('originalTextFromImage');
    const outputErrorMessages = document.getElementById('errorText');
    

    outputErrorMessages.innerHTML = "";

    if(scanTextButton)
    {
        scanTextButton.addEventListener("click", handleExtractButtonClick);
        
    }
    else
    {
        console.error("ERROR - No scan button was found");
    }

    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {

    if(request.type === "IMAGE_DATA_URL_FOUND" && request.imageDataURL)
    {
        console.log("Success - The image has been converted into base 64");
        if(originalTextInput)
        {
            originalTextInput.innerHTML = "<p>The Image has been received. Beginning Translation process</p>";
            imageOCR(request.imageDataURL);
        }
    }
    else if(request.type === "NO_IMAGE_FOUND_ON_PAGE")
    {
        console.log("Error - No image has been found on the page");
        outputErrorMessages.innerHTML = "<p>No Image has been found on the page</p>";
    }
    else if(request.type === "IMAGE_PROCESSING_ERROR")
    {
        console.log("Error - An error has been reported by the script: ", request.message);
        outputErrorMessages.innerHTML = `<p>Error processing image on page: ${request.message}</p>`;
    }

    });

});



function handleExtractButtonClick() {


    const originalTextInput = document.getElementById('originalTextFromImage');
    const progressBarContainerJS = document.getElementById('progressBarContainer');

    console.log("Message - Extract button was clicked");

    progressBarContainerJS.style.display = "block";

    if(originalTextInput)
    {
        originalTextInput.innerHTML = "<p>Scanning page for image....</p>";
    }

    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        
        if(chrome.runtime.lastError)
        {
            console.error("Error - Cannot query tabs: ", chrome.runtime.lastError.message);
            if(originalTextInput)
            {
                originalTextInput.innerHTML = "<p>Error - Could not find an active tab</p>";
                return;
            }
        }

        const activeTab = tabs[0];

        if(activeTab && activeTab.id)
        {
            console.log("Running imageExtractor script on current tab");

            chrome.scripting.executeScript({target: {tabId: activeTab.id}, files: ['imageExtractor.js']}, () => {

                if(chrome.runtime.lastError)
                {
                    console.error("Error - Cannot run imageExtractor script: ", chrome.runtime.lastError.message);
                    
                    if(originalTextInput)
                    {
                        originalTextInput.innerHTML = "<p>Error: Cannot scan this page</p>";
                    }
                    else
                    {
                        console.log("Success - script has ran successfully");
                    }
                }
            });
        }
        else
        {
            console.error("Error - Cannot find a valid tab ID");
            if(originalTextInput)
            {
                originalTextInput.innerHTML = "<p>Error - No valid tab found</p>";
            }
        }
    });
}


async function imageOCR(imageDataURL) {
    const originalTextInput = document.getElementById('originalTextFromImage');
    const outputErrorMessages = document.getElementById('errorText');
    const scannedMessage = document.getElementById('scannedHeader');
    const progressBarContainerJS = document.getElementById('progressBarContainer');
    const progressBarLoaderJS = document.getElementById('progressBarLoader');
    const translatedTextMessage = document.getElementById('translatedText')
    const translatedTextHeader = document.getElementById('translatedHeader')

    outputErrorMessages.innerHTML = "";
    translatedTextMessage.innerHTML = "";

    
    try {

        setTimeout(() => {

            progressBarLoaderJS.style.width = '10%';
            progressBarLoaderJS.innerHTML = '10%';
        }, 1500);

        setTimeout(() => {

            progressBarLoaderJS.style.width = '25%';
            progressBarLoaderJS.innerHTML = '25%';
        }, 2000);

        setTimeout(() => {

            progressBarLoaderJS.style.width = '50%';
            progressBarLoaderJS.innerHTML = '50%';
        }, 2500);


        setTimeout(() => {

            progressBarLoaderJS.style.width = '85%';
            progressBarLoaderJS.innerHTML = '85%';
        }, 3000);

        const response = await fetch('http://localhost:3000/ocr', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ imageDataUrl: imageDataURL })
        });


        const dataFromServer = await response.json();

        if (!response.ok || dataFromServer.status === 'error') 
        {
            throw new Error(dataFromServer.message || 'An error occurred on the server.');
        }


        setTimeout(() => {

            progressBarLoaderJS.style.width = '100%';
            progressBarLoaderJS.innerHTML = '100%';
        }, 3500);
    

        const textExtracted = dataFromServer.text;
        const translatedTextExtracted = dataFromServer.translated_final_text
        console.log("Success - Data has been received from the server:", textExtracted);


        if (textExtracted && textExtracted.trim() !== "") 
        {
            scannedMessage.innerHTML = 'The scanned text is below:';
            originalTextInput.innerHTML = `<pre>${textExtracted}</pre>`;
            translatedTextHeader.innerHTML = 'The translated scanned text is below:'
            translatedTextMessage.innerHTML = `<pre>${translatedTextExtracted}</pre>`

        } 
        else 
        {
            originalTextInput.innerHTML = "<p>The server did not find any text.</p>";
        }

    }
    catch (error) 
    {
        console.error("Error communicating with OCR server:", error);
        outputErrorMessages.textContent = `Error: ${error.message}`;
        progressBarContainerJS.style.display = "none";
    }

    progressBarContainerJS.style.display = "none";
    progressBarLoaderJS.style.width = "0%";
    progressBarLoaderJS.innerHTML = "0%";
}


