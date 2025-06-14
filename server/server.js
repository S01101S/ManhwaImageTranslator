const express = require('express');
const { spawn } = require('child_process');
const bodyParser = require('body-parser');
const cors = require('cors');

const app = express();
const port = 3000;

app.use(cors());
app.use(bodyParser.json({ limit: '100mb' }));
app.use(bodyParser.urlencoded({ limit: '100mb', extended: true }));

app.post('/ocr', (req, res) => {
    const imageDataUrl = req.body.imageDataUrl;
    if (!imageDataUrl) {
        return res.status(400).json({ error: 'No image data URL provided.' });
    }


    //Change the python file name in the line below to switch between different speech bubble detection languages
    const pythonProcess = spawn('python', ['koreanSpeechBubbleDetection.py']);

    let pythonOutput = '';
    let pythonError = '';

    
    pythonProcess.stdin.write(imageDataUrl);
    pythonProcess.stdin.end();

    pythonProcess.stdout.on('data', (data) => {
        pythonOutput += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        pythonError += data.toString();
        console.error(`PYTHON_STDERR: ${data}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process exited with code ${code}`);


        if (code === 0 && pythonOutput) 
            {
            try 
            {
            
                const jsonData = JSON.parse(pythonOutput);
                res.status(200).json(jsonData);
            
            } catch (e) 
            {
            
                res.status(500).json({ error: 'Failed to parse result from Python script.' });
            }
        }

        else 
        {
        
            res.status(500).json({ error: `OCR processing failed: ${pythonError}` });
        }
    });

    pythonProcess.on('error', (err) => {
        console.error('Failed to spawn Python process:', err);
        res.status(500).json({ error: 'Server could not start the OCR process.' });
    });
});

app.listen(port, () => {
    console.log(`Node.js OCR server listening on http://localhost:${port}`);
});


