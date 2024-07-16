var pivot_projects = []
var project_tags = {}

const get_pivot_projects = async () => {
  let pivot_projects_response = await fetch("/pivot_projects")
    .then(response => response.json());
  pivot_projects = pivot_projects_response

  let pivot_projects_select = document.getElementById("pivot-project-select");
  pivot_projects.map((pivot_project) => {
    let option = document.createElement("option");
    option.value = pivot_project;
    option.innerHTML = pivot_project;
    pivot_projects_select.append(option);
  })
}

const get_pivot_projects_tags = async () => {
  for (let pivot_project of pivot_projects) {
    if (!(pivot_project in project_tags)) {
      project_tags[pivot_project] = []
    }

    let project_tags_response = await fetch(`/project/tags?project_path=${pivot_project}`)
      .then(response => response.json());

    for (const [_, project_tag] of Object.entries(project_tags_response)) {
      project_tags[pivot_project].push(project_tag)
    }
  }
}

const fill_pivot_projects_tags_select = () => {
  let pivot_projects_select = document.getElementById("pivot-project-select");
  let current_project = pivot_projects_select.value;
  let pivot_project_tags_select = document.getElementById("project-tag-select");
  for (const project_tag of project_tags[current_project]) {
    let option = document.createElement("option");
    option.value = project_tag;
    option.innerHTML = project_tag;
    pivot_project_tags_select.append(option);
  }
}

get_pivot_projects().then(
  () => {
    get_pivot_projects_tags().then(
      () => {
        fill_pivot_projects_tags_select()
        draw_diagram_event(null)
      }
    )
  }
)

const draw_diagram_event = async () => {
  let pivot_projects_select = document.getElementById("pivot-project-select");
  let pivot_project_tags_select = document.getElementById("project-tag-select");
  let current_project = pivot_projects_select.value;
  let current_tag = pivot_project_tags_select.value;
  const full_deps = await fetch(`/project/deps?project_path=${current_project}&project_tag=${current_tag}`)
    .then(response => response.json())
    .catch(e => {
      console.log("Error happened!")
      console.log(e)
    });

  let diagram_type_select = document.getElementById("diagram-type-select");

  console.log(diagram_type_select.value)
  if (diagram_type_select.value == "round") {
    draw_round_tree_diagram(full_deps)
  } else {
    draw_collapse_basic_tree(full_deps)
  }
}

const color_based_on_dep_provider = (d) => {
  if (d.data.deps_provider === undefined) {
    return "#aaa";
  }
  const lowerCase = d.data.deps_provider.toLowerCase();
  if (lowerCase.startsWith("conanfile")) {
    return "#19abb2";
  } else if (lowerCase.startsWith("dockerfile")) {
    return "#b4a1c6";
  } else if (lowerCase.startsWith("requirements")) {
    return "#dacc5a";
  } else if (lowerCase.startsWith("docker-compose")) {
    return "#c3445a";
  }
}

const mocks = () => {
  let diagram_type_select = document.getElementById("diagram-type-select");
  fetch(`mock_deps.json`)
  .then(response => response.json())
  .then(response => {
    
    if (diagram_type_select.value == "round") {
      draw_round_tree_diagram(response)
    } else {
      draw_collapse_basic_tree(response)
    }
  })
}

const clear_diagram = () => {
  d3.selectAll("#my_dataviz > *").remove();
}

const collapse = (d) => {
  if (d.children) {
    d._children = d.children
    d._children.forEach(collapse)
    d.children = null
  }
}

const draw_collapse_basic_tree = (data) => {
  // Create the cluster layout:
  const root = d3.hierarchy(data);
  let max_depth = 0;
  for (const node of root.descendants()) {
    if (node.depth > max_depth) {
      max_depth = node.depth;
    }
  }
  const treemap = d3.tree(data).nodeSize([35, 300]);
  treemap(root);

  root.children.forEach(collapse);

  const collapseToggle = (_, d) => {
    if (d.children) {
      d._children = d.children
      d._children.forEach(collapse)
      d.children = null
    } else {
      d.children = d._children
      d._children = null
    }
    update_basic_tree_diagram(d)
  }

  const update_basic_tree_diagram = (source) => {
    clear_diagram();
    treemap(root);
    const width = 1600;
  
    let min_x = Number.MAX_SAFE_INTEGER;
    let max_x = -min_x;
    for (const node of root.descendants()) {
      if (node.x > max_x) {
        max_x = node.x;
      }
      if (node.x < min_x) {
        min_x = node.x;
      }
    }
    let height = max_x + Math.abs(min_x) + 100;
    console.log(max_x, min_x, height)
  
    const svg = d3.select("#my_dataviz")
      .append("svg")
      .attr("width", width)
      .attr("height", height)
      .append("g")
      .attr("id", "main_group")
      .attr("transform", `translate(40,${height / 2})`)  // bit of margin on the left = 40
  
    // Add the links between nodes:
    svg.selectAll('path')
      .data(root.descendants().slice(1))
      .join('path')
      .attr("d", function (d) {
        return "M" + d.y + "," + d.x
          + "C" + (d.parent.y + 100) + "," + d.x
          + " " + (d.parent.y + 100) + "," + d.parent.x // 50 and 150 are coordinates of inflexion, play with it to change links shape
          + " " + d.parent.y + "," + d.parent.x;
      })
      .style("fill", 'none')
      .attr("stroke", color_based_on_dep_provider)
  
    svg.selectAll("g")
      .data(root.descendants())
      .join("g")
      .attr("transform", function (d) {
        return `translate(${d.y},${d.x})`
      })
      .append("circle")
      .attr("r", 8)
      .style("fill", color_based_on_dep_provider)
      .attr("stroke", (d) => {
        if (d._children) {
          return "#3bcc58"
        }
        if (d.children) {
          return "#2e7f48"
        }
        return "black"
      })
      .style("cursor", (d) => {
        return d._children || d.children ? "pointer" : "default";
      })
      .style("stroke-width", 2.5)
      .on("click", collapseToggle)
  
    svg.selectAll("g")
      .data(root.descendants())
      .join("g")
      .attr("transform", function (d) {
        return `translate(${d.y},${d.x})`
      })
      .append("text")
      .attr("x", function (d) { return d.parent ? d.children ? 0 : +10 : +10; })
      .attr("y", function (d) { return d.parent ? d.children ? -8 : +4 : +4; })
      .style("text-anchor", function (d) {
        return d.parent ? d.children ? "middle" : "start" : "start";
      })
      .style("font-weight", "400")
      .text(function (d) { return d.data.name; })
  }

  update_basic_tree_diagram(root)
}

const draw_basic_tree_diagram = (data) => {
  clear_diagram();
  const width = 1600;


  // Create the cluster layout:
  const root = d3.hierarchy(data);
  let max_depth = 0;
  for (const node of root.descendants()) {
    if (node.depth > max_depth) {
      max_depth = node.depth;
    }
  }
  const treemap = d3.tree(data).nodeSize([35, (width - 200) / max_depth]);
  treemap(root);

  let min_x = Number.MAX_SAFE_INTEGER;
  let max_x = -min_x;
  for (const node of root.descendants()) {
    if (node.x > max_x) {
      max_x = node.x;
    }
    if (node.x < min_x) {
      min_x = node.x;
    }
  }
  let height = max_x + Math.abs(min_x) + 100;

  const svg = d3.select("#my_dataviz")
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("id", "main_group")
    .attr("transform", `translate(40,${height / 2})`)  // bit of margin on the left = 40

  // Add the links between nodes:
  svg.selectAll('path')
    .data(root.descendants().slice(1))
    .join('path')
    .attr("d", function (d) {
      return "M" + d.y + "," + d.x
        + "C" + (d.parent.y + 100) + "," + d.x
        + " " + (d.parent.y + 100) + "," + d.parent.x // 50 and 150 are coordinates of inflexion, play with it to change links shape
        + " " + d.parent.y + "," + d.parent.x;
    })
    .style("fill", 'none')
    .attr("stroke", color_based_on_dep_provider)

  svg.selectAll("g")
    .data(root.descendants())
    .join("g")
    .attr("transform", function (d) {
      return `translate(${d.y},${d.x})`
    })
    .append("circle")
    .attr("r", 8)
    .style("fill", color_based_on_dep_provider)
    .attr("stroke", "black")
    .style("stroke-width", 0.5)

  svg.selectAll("g")
    .data(root.descendants())
    .join("g")
    .attr("transform", function (d) {
      return `translate(${d.y},${d.x})`
    })
    .append("text")
    .attr("x", function (d) { return d.parent ? d.children ? 0 : +10 : +10; })
    .attr("y", function (d) { return d.parent ? d.children ? -8 : +4 : +4; })
    .style("text-anchor", function (d) {
      return d.parent ? d.children ? "middle" : "start" : "start";
    })
    .style("font-weight", "400")
    .text(function (d) { return d.data.name; })
}

const draw_round_tree_diagram = (data) => {
  d3.selectAll("#my_dataviz > *").remove();
  const width = window.screen.width / 2
  const radius = width / 2 // radius of the dendrogram
  const height = radius * 2

  // append the svg object to the body of the page
  const svg = d3.select("#my_dataviz")
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .append("g")
    .attr("transform", `translate(${radius},${radius})`);

  // read json data
  // Create the cluster layout:
  const cluster = d3.tree()
    .size([360, radius - 160]);  // 360 means whole circle. radius - 60 means 60 px of margin around dendrogram

  // Give the data to this cluster layout:
  const root = d3.hierarchy(data, function (d) {
    return d.children;
  });
  cluster(root);
  root.children.forEach(collapse);

  cluster(root);

  // Features of the links between nodes:
  const linksGenerator = d3.linkRadial()
    .angle(function (d) { return d.x / 180 * Math.PI; })
    .radius(function (d) { return d.y; });

  // Add the links between nodes:
  svg.selectAll('path')
    .data(root.links())
    .join('path')
    .attr("d", linksGenerator)
    .style("fill", 'none')
    .attr("stroke", '#ccc')


  // Add a circle for each node.
  svg.selectAll("g")
    .data(root.descendants())
    .join("g")
    .attr("transform", function (d) {
      return `rotate(${d.x - 90})
        translate(${d.y})`;
    })
    .append("circle")
    .attr("r", 7)
    .style("fill", "#69b3a2")
    .attr("stroke", "black")
    .style("stroke-width", 2);
  svg.selectAll("g")
    .data(root.descendants())
    .join("g")
    .append("text")
    .attr("transform", (d) => {
      return `rotate(${-1 * (d.x - 90)})
        translate(0)`
    })
    .style("text-anchor", "start")
    .text(function (d) { return d.data.name; })
}
