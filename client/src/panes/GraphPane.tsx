import React from "react";
import SplitPane from "react-split-pane";

import Header from "../components/Header";
import Graph from "../components/Graph";

import "../index.css";

// used https://openclassrooms.com/en/courses/4286486-build-web-apps-with-reactjs/4286711-build-a-ticking-clock-component
// blog.cloudboost.io/for-loops-in-react-render-no-you-didnt-6c9f4aa73778

const GraphPane = () => (
  <div>
    <Header>Graphs</Header>
    <div className="h-full border-2">
      <SplitPane
        style={{ marginTop: "32px" }}
        className="view"
        split="horizontal"
        size="50%"
      >
        <Graph />
        <Graph />
      </SplitPane>
    </div>
  </div>
);

export default GraphPane;
