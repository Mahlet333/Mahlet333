Real-Time Attention Detection Toolkit

Description:
This repository contains two projects focused on real-time attention detection: a JavaScript-based attention contagion simulator and a Flask-based real-time attention level prediction web application. These projects aim to explore and simulate the dynamics of attention within educational settings and provide a practical tool for predicting attention levels using webcam feed data.

JavaScript Attention Contagion Simulator:

Description: This simulator models the spread of attention within an in-person classroom setting, considering factors such as proximity to the teacher, seating arrangement, environmental stimuli, and social interactions.

Features:

Dynamic simulation of attention contagion dynamics.
Real-time visualization of attention levels within the simulated classroom.
Customizable parameters for exploring different classroom scenarios.
Interactive controls for starting, pausing, and adjusting simulation parameters.
Flask Real-Time Attention Level Prediction Web App:

Description: This web application predicts real-time attention levels using a webcam feed. It extracts features related to attention levels from each video frame, such as face presence and head orientation, and uses a Support Vector Machine (SVM) model for prediction.

Features:

Integration of webcam functionality for real-time video capture.
Face detection using OpenCV's face cascade classifier.
Feature extraction from video frames for attention level prediction.
Real-time updates of attention level predictions.
User-friendly web interface for viewing webcam feed and predictions.

Usage:

Clone the repository to your local machine.

For the JavaScript simulator:

Open index.html in a web browser to launch the simulator.
Adjust simulation parameters using the provided controls.

For the Flask web application:

Install dependencies by running pip install -r requirements.txt.
Run the Flask application with python app.py.
Access the web interface at http://localhost:5000 and grant webcam access.
Observe real-time predictions of attention levels based on the webcam feed.

Contributing:
Contributions to this project are welcome! If you have ideas for improvements or new features, feel free to open an issue or submit a pull request.

License:
This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgements:
Special thanks to the contributors of OpenCV, p5.js, and the developers of the pre-trained SVM model used for attention level prediction.

Authors:
Mahlet Atrsaw Andargei
