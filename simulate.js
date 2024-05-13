let nodes = [];
let circleRadius = 0;
let circleGrowthRate = 1;
let focusX, focusY;
let numRows = 10;
let numCols = 10;
let nodeSize = 20;
let nodeSpacing = 50;

let applyA = false;
let applyB = false;
let aDuration = 0;
let bDuration = 0;
let aStartTime, bStartTime;

let susceptibleNodes = 0;
let influentialNodes = 0;
let resistantNodes = 0;

let isSimulating = false;

let slider;

function setup() {
  createCanvas(800, 800);
  
  // Create slider for growth rate
  slider = createSlider(1, 10, 5, 1);
  slider.position(20, 20);
  
  // Create "Set" and "Simulate" buttons
  let setButton = createButton("Set");
  setButton.position(20, 50);
  setButton.mousePressed(setInitialState);
  
  let simulateButton = createButton("Simulate");
  simulateButton.position(20, 80);
  simulateButton.mousePressed(startSimulation);
  
  // Create 100 nodes in a grid with different characteristics
  setInitialState();
}

function setInitialState() {
  // Clear previous nodes
  nodes = [];
  susceptibleNodes = 0;
  influentialNodes = 0;
  resistantNodes = 0;
  
  // Create new nodes with initial classifications
  for (let row = 0; row < numRows; row++) {
    for (let col = 0; col < numCols; col++) {
      let x = col * nodeSpacing + nodeSize / 2;
      let y = row * nodeSpacing + nodeSize / 2;
      
      // Assign initial levels based on classification
      let classification = floor(random(1, 11)); // Random initial classification
      let nodeColor;
      if (classification <= 3) {
        nodeColor = color(255, 0, 0); // Red for susceptible
        susceptibleNodes++;
      } else if (classification <= 6) {
        nodeColor = color(255, 255, 0); // Yellow for influential
        influentialNodes++;
      } else {
        nodeColor = color(0, 255, 0); // Green for resistant
        resistantNodes++;
      }
      
      nodes.push(new Node(x, y, classification, nodeColor));
    }
  }
  
  // Set the focal point to a random position
  focusX = random(width);
  focusY = random(height);
  
  // Reset the circle radius
  circleRadius = 0;
  
  // Reset the simulation state
  isSimulating = false;
}

function startSimulation() {
  isSimulating = true;
  circleGrowthRate = slider.value();
}

function draw() {
  background(255);
  
  // Draw the growing circle
  fill(255, 0, 0, 100);
  noStroke();
  circle(focusX, focusY, circleRadius * 2);
  
  // Update the circle radius
  if (isSimulating) {
    if (applyA) {
      // Apply mechanism A to push back the circle
      circleRadius = max(0, circleRadius - 2);
      aDuration--;
      if (aDuration <= 0) {
        applyA = false;
      }
    } else if (applyB) {
      // Apply mechanism B to slow down the circle
      circleRadius += 0.5;
      bDuration--;
      if (bDuration <= 0) {
        applyB = false;
      }
    } else {
      // Normal circle growth
      let growthRate = circleGrowthRate;
      
      // Increase the growth rate based on the number of susceptible and influential nodes, but with a smaller effect
      growthRate += 0.05 * (susceptibleNodes + influentialNodes);
      
      circleRadius += growthRate;
    }
  }
  
  // Draw the nodes
  for (let node of nodes) {
    // Check if the node is inside the circle
    let distance = dist(node.x, node.y, focusX, focusY);
    if (distance <= circleRadius) {
      // Update the node's classification based on its initial classification
      let classification = node.classification;
      if (classification <= 3) {
        classification = min(classification + 1, 3); // Increase susceptibility for susceptible individuals
        susceptibleNodes++;
      } else if (classification >= 7) {
        classification = max(classification - 1, 1); // Decrease resistance for resistant individuals
        resistantNodes--;
        susceptibleNodes++;
      } else {
        // Influential individuals may fluctuate within the 4-6 range
        classification = constrain(classification + floor(random(-1, 2)), 4, 6);
        influentialNodes++;
      }
      
      // Update node color based on new classification
      let nodeColor;
      if (classification <= 3) {
        nodeColor = color(255, 0, 0); // Red for susceptible
      } else if (classification <= 6) {
        nodeColor = color(255, 255, 0); // Yellow for influential
      } else {
        nodeColor = color(0, 255, 0); // Green for resistant
      }
      
      // Turn the node red based on its characteristics
      fill(nodeColor);
      circle(node.x, node.y, nodeSize);
      
      // Display the classification on top of the node
      fill(0);
      textSize(12);
      textAlign(CENTER, CENTER);
      text(classification, node.x, node.y);
      
      // Update the node's classification
      node.classification = classification;
      node.nodeColor = nodeColor;
    } else {
      // Keep the node in its original color
      fill(200);
      circle(node.x, node.y, nodeSize);
    }
  }
  
  // Display the active mechanism
  textSize(24);
  textAlign(RIGHT, TOP);
  fill(0);
  if (applyA) {
    text("A", width - 20, 20);
  } else if (applyB) {
    text("B", width - 20, 20);
  }
  
  // Apply mechanisms A and B randomly
  if (isSimulating) {
    if (random() < 0.005) {
      // Apply mechanism A
      applyA = true;
      aDuration = random(60, 120);
      aStartTime = millis();
    }
    
    if (random() < 0.005) {
      // Apply mechanism B
      applyB = true;
      bDuration = random(60, 120);
      bStartTime = millis();
    }
  }
}

class Node {
  constructor(x, y, classification, nodeColor) {
    this.x = x;
    this.y = y;
    this.classification = classification;
    this.nodeColor = nodeColor;
  }
}
