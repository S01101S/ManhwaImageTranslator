(async () =>
{
    console.log("[Content Script] imageExtractor.js has started.");

    const imageChecker = async () => {
        console.log("[Content Script] imageChecker function is now running...");
        console.log("[Content Script] imageChecker: Checking for document images.");

        if(document.images && document.images.length > 0)
        {
            console.log("[Content Script] imageChecker: Found images, returning the first one.");
            return document.images[0];
        }
        else
        {
            console.log("[Content Script] imageChecker: No images found on the page.");
            return null; 
        }
    };

    let foundElement = await imageChecker();

    if (foundElement)
    {
        try {
            const convertImageIntoCanvas = (imageElement) => {
                console.log("[Content Script] Converting image to data URL using canvas.");

                const canvas = document.createElement('canvas');
                const canvas2D = canvas.getContext('2d');

                canvas.width = imageElement.naturalWidth * 2.5;
                canvas.height = imageElement.naturalHeight * 2.5;

                canvas2D.drawImage(imageElement, 0, 0, canvas.width, canvas.height); 
              
                const imageDataURL = canvas.toDataURL('image/png');

                console.log("base64String generated (first 50 chars): ", imageDataURL.substring(0, 50) + "...");

                if(imageDataURL && imageDataURL.length > 50)
                {
                    console.log("[Content Script] Image converted successfully.");
                    chrome.runtime.sendMessage({type:"IMAGE_DATA_URL_FOUND", imageDataURL: imageDataURL});
                }
                else
                {
                    throw new Error("Canvas failed to generate a valid data URL or it was too short.");
                }
            };

            if(!foundElement.complete || foundElement.naturalHeight === 0)
            {
                console.log("[Content Script] Image has not loaded in yet, waiting for load event.");
                foundElement.addEventListener('load', function handler(){
                    foundElement.removeEventListener('load', handler);
                    convertImageIntoCanvas(foundElement);
                });
            }
            else
            {
                console.log("[Content Script] Image already loaded.");
                convertImageIntoCanvas(foundElement);
            }

        }
        catch (error) {
            console.error("[Content Script] Error during canvas conversion:", error);
            chrome.runtime.sendMessage({ type: "IMAGE_PROCESSING_ERROR", message: "Error converting image to canvas data." });
        }

    }
    else
    {
        console.log("[Content Script] imageChecker was called but found no image by its criteria.");
        chrome.runtime.sendMessage({ type: "NO_IMAGE_FOUND_ON_PAGE" });
    }

})();