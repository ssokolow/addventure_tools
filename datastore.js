/* TODO: Figure out which newer ECMAScript constructs are safe to use */
// --== Abstraction to provide horizon'd views ===--
var setdefault = function(obj, key, def) {
    if (!obj.hasOwnProperty(key)) { obj[key] = def; }
    return obj[key];
};

// IMPORTANT: This assumes exclusive responsibility for the given records
//            and will freeze or manipulate fields on them.
var DataStore = function(records) {
  this.records = Object.freeze(records); // Note: "records" is frozen too
  this.by_id = {};
  this.children = {};

  // Chosen to keep performance acceptable in Vis.js
  // 6^3 + 6^3
  var MAX_ANCESTOR_LEVEL = 3;
  var MAX_DESCENDANT_LEVEL = 3;

  // Work around 'this' vagarities
  var self = this;

  // Build indexes
  for (let record of this.records) {
    // Build the by-id index and freeze record IDs
    // (but still allow the records themselves to be mutated)
    this.by_id[record.id] = record;
    Object.defineProperty(record, 'id', {
      "enumerable": true,
      "value": record.id
    });

    // Build the parent->child index
    var child_list = setdefault(this.children, record.parent_id, []);
    child_list.push(record);
  }

  // Freeze both indexes
  Object.freeze(this.by_id);
  Object.freeze(this.children);
  for (let key of Object.keys(this.children)) {
    if (this.children.hasOwnProperty(key)) {
      Object.freeze(this.children[key]);
    }
  }

  // Return the number of child nodes for the given node
  this.count_children = function(id) {
    return this.get_children(id).length
  }

  // Return the frozen list of child nodes for the given node
  this.get_children = function(id) {
    if (id === null) { return []; }
    if (!(typeof id == "number")) { id = id.id; }
    if (!this.children.hasOwnProperty(id)) { return []; }
    return this.children[id];
  }

  // Return the parent for the given node
  this.get_parent = function(id) {
    if (id === null) { return null; }
    if (!(typeof id == "number")) { id = id.id; }
    if (!this.by_id.hasOwnProperty(id)) { return null; }
    return this.by_id[id].parent_id;
    // TODO: Add a unit test suite, then figure out why this fails.
  }

  // return a list of "root"'s siblings, ancestors, and ancestor's
  // siblings by ascending "limit" levels.
  this.recurse_ancestors = function(root, limit) {
    if (!(typeof root == "number")) { root = root.id; }
    var results = [];
    for (var i = 0; i < limit; i++) {
      var parent = this.get_parent(root);
      if (parent === null) {
        results.push(this.by_id[root]);
        break;
      } else {
        root = parent;
        $.merge(results, this.get_children(root));
      }
    }
    return results;
  }

  // return a list containing root's descendants
  // "level" is optional and defaults to 0
  this.recurse_descendants = function(root, limit, level) {
    if (typeof level === 'undefined') { level = 0; }

    // recurse_dependencies is defined to exclude "root" so it's easy to
    // pair with recurse_ancestors without duplicating it.
    var results = [];
    if (level > 0) { results.push(root); }

    if (level < limit) {
      for (let child of this.get_children(root.id)) {
        $.merge(results, self.recurse_descendants(child, limit,
                                                  level + 1));
      }
    }
    return results;
  };

  // Get a horizon'd, vis.js-compatible view
  this.get_view = function(current_id) {
    var center = this.by_id[current_id];

    // Build nodes list
    var nodes = $.merge(
        this.recurse_ancestors(center, MAX_ANCESTOR_LEVEL),
        this.recurse_descendants(center, MAX_DESCENDANT_LEVEL));

    // Annotate nodes for graph view
    for (let node of nodes) {
      node.label = node.title;
    }
    // TODO: Indicate omitted edges somehow

    // Build edges list
    var edges = [];
    for (let parent of nodes) {
      for (let child of this.get_children(parent)) {
        edges.push({
            from: parent.id,
            to: child.id
        });
      }
    }

    return {
      'nodes': nodes,
      'edges': edges
    }
  };

  // TODO: Complete this
};

