// @ts-check
// Static fixture data for the mock engine: stations, boarding points, lines and a
// hand-built multi-level walking network of Bern station. Coordinates of the Bern
// boarding points are the real registry (atlas) coordinates.

/** @import { Quay, Mode, QuaySide, LineBadge, Place, IndoorFeatureProps } from '../src/api/types.ts' */

/**
 * @typedef {Object} Station
 * @property {string} key
 * @property {string} id
 * @property {string} didok
 * @property {string} name
 * @property {number} lat
 * @property {number} lon
 * @property {Quay[]} quays
 * @property {Mode[]} modes
 */

/** @type {Record<string, Station>} */
export const stations = {};
/** @type {Record<string, Quay>} */
export const quaysById = {};
/** quay id → walk-graph node ids it is attached to @type {Record<string, string[]>} */
export const quayNodes = {};

/**
 * @param {string} key @param {string} didok @param {string} name @param {number} lat @param {number} lon
 */
function st(key, didok, name, lat, lon) {
  stations[key] = { key, id: "st:" + didok, didok, name, lat, lon, quays: [], modes: [] };
}

/**
 * @param {string} dir compass side
 * @param {string} street
 * @param {QuaySide["of"]} [of]
 * @returns {QuaySide}
 */
function side(dir, street, of = "road") {
  const names = { N: "north", NE: "north-east", E: "east", SE: "south-east", S: "south", SW: "south-west", W: "west", NW: "north-west" };
  const what = of === "rail-track" ? "the tracks" : street || (of === "tram-track" ? "the tram tracks" : "the road");
  return { street, side: /** @type {QuaySide["side"]} */ (dir), of, text: `${names[/** @type {keyof typeof names} */ (dir)]} side of ${what}` };
}

/**
 * @param {string} stKey
 * @param {string} label
 * @param {number} lat
 * @param {number} lon
 * @param {Partial<Quay> & { nodes?: string[], key?: string }} [o]
 */
function q(stKey, label, lat, lon, o = {}) {
  const s = stations[stKey];
  const { nodes, key, ...rest } = o;
  const suffix = key ?? (label || String(s.quays.length + 1));
  /** @type {Quay} */
  const quay = {
    id: `${s.didok}:0:${suffix}`,
    sloid: `ch:1:sloid:${Number(s.didok) - 8500000}:0:${suffix}`,
    stationId: s.id,
    stationName: s.name,
    label,
    noun: "edge",
    lat,
    lon,
    precision: "edge",
    modes: [],
    ...rest,
  };
  s.quays.push(quay);
  quaysById[quay.id] = quay;
  if (nodes) quayNodes[quay.id] = nodes;
  return quay;
}

// ---------------------------------------------------------------- Bern hub

st("bern", "8507000", "Bern", 46.948832, 7.439131);
st("bernbhf", "8576646", "Bern, Bahnhof", 46.948105, 7.440209);
st("bernpost", "8507785", "Bern, Hauptbahnhof", 46.948996, 7.438527);
st("hirsch", "8579896", "Bern, Hirschengraben", 46.946063, 7.437779);
st("schanz", "8581351", "Bern, Schanzenstrasse", 46.947943, 7.437174);

/** @type {[string, number, number, string, string][]} */
const railTracks = [
  ["1", 46.948412, 7.437986, "12", "S"],
  ["2", 46.948454, 7.437839, "12", "N"],
  ["3", 46.948393, 7.437289, "34", "S"],
  ["4", 46.948445, 7.437247, "34", "N"],
  ["5", 46.948507, 7.437208, "56", "S"],
  ["6", 46.948564, 7.43714, "56", "N"],
  ["7", 46.948566, 7.43683, "78", "S"],
  ["8", 46.948642, 7.436779, "78", "N"],
  ["9", 46.948929, 7.43757, "910", "S"],
  ["10", 46.949085, 7.437762, "910", "N"],
  ["12", 46.949214, 7.43778, "1213", "S"],
  ["13", 46.949288, 7.437715, "1213", "N"],
];
for (const [label, lat, lon, p, sd] of railTracks) {
  q("bern", label, lat, lon, { noun: "track", level: 0, access: "autonomous", nodes: ["p" + p, "pw" + p], side: side(sd, "", "rail-track") });
}
q("bern", "49", 46.948227, 7.43333, { noun: "track", level: 0, access: "assisted", nodes: ["p4950"] });
q("bern", "50", 46.94831, 7.433557, { noun: "track", level: 0, access: "assisted", nodes: ["p4950"] });
q("bern", "21", 46.94965, 7.43989, { noun: "track", level: -2, access: "autonomous", nodes: ["rbs12"] });
q("bern", "22", 46.94956, 7.43985, { noun: "track", level: -2, access: "autonomous", nodes: ["rbs12"] });
q("bern", "23", 46.94951, 7.43983, { noun: "track", level: -2, access: "autonomous", nodes: ["rbs34"] });
q("bern", "24", 46.94944, 7.43982, { noun: "track", level: -2, access: "autonomous", nodes: ["rbs34"] });

/** @type {[string, number, number, string, QuaySide][]} */
const bays = [
  ["A", 46.947568, 7.440602, "bald", side("S", "Bubenbergplatz", "tram-track")],
  ["B", 46.947666, 7.440629, "bald", side("N", "Bubenbergplatz", "tram-track")],
  ["C", 46.94758, 7.440072, "bald", side("S", "Bubenbergplatz", "tram-track")],
  ["D", 46.947666, 7.44018, "bald", side("N", "Bubenbergplatz", "tram-track")],
  ["E", 46.948206, 7.440009, "bhp", side("W", "Bahnhofplatz")],
  ["F", 46.947856, 7.439892, "bhp", side("E", "Bahnhofplatz")],
  ["G", 46.948604, 7.44044, "bol", side("W", "Bollwerk")],
  ["H", 46.949089, 7.440296, "bol", side("W", "Bollwerk")],
  ["I", 46.947359, 7.440997, "bubS", side("N", "Bubenbergplatz")],
  ["J", 46.946795, 7.44097, "chr", side("W", "Christoffelgasse")],
  ["K1", 46.946875, 7.440772, "chr", side("S", "Bubenbergplatz")],
  ["K2", 46.946648, 7.440871, "chr", side("W", "Schwanengasse")],
  ["L", 46.947298, 7.440548, "bubS", side("S", "Bubenbergplatz")],
  ["M", 46.947377, 7.439683, "bubW", side("S", "Bubenbergplatz")],
  ["N", 46.947047, 7.438967, "hgN", side("E", "Hirschengraben", "tram-track")],
  ["Q", 46.947593, 7.439368, "bubW", side("N", "Bubenbergplatz")],
  ["Z", 46.949046, 7.440701, "bol", side("E", "Bollwerk")],
];
for (const [label, lat, lon, node, sd] of bays) {
  q("bernbhf", label, lat, lon, { noun: "bay", access: label === "K2" || label === "Z" ? "assisted" : "autonomous", nodes: [node], side: sd });
}

/** @type {[string, number, number][]} */
const deckBays = [
  ["R", 46.949041, 7.438751],
  ["S", 46.949, 7.438645],
  ["T", 46.948959, 7.43858],
  ["U", 46.948924, 7.438516],
  ["V", 46.948894, 7.438442],
  ["W", 46.948858, 7.438372],
  ["X", 46.94883, 7.438315],
  ["Y", 46.948735, 7.438829],
];
for (const [label, lat, lon] of deckBays) q("bernpost", label, lat, lon, { noun: "bay", level: 2, access: "autonomous", nodes: ["deck"] });

/** @type {[string, number, number, string, QuaySide][]} */
const hg = [
  ["A", 46.946427, 7.43752, "hgS", side("W", "Hirschengraben", "tram-track")],
  ["B", 46.94685, 7.437745, "hgN", side("E", "Hirschengraben", "tram-track")],
  ["C", 46.946985, 7.43814, "hgN", side("E", "Hirschengraben")],
  ["D", 46.945979, 7.438086, "hgS", side("N", "Bundesgasse")],
  ["E", 46.947157, 7.437206, "hgN", side("S", "Laupenstrasse")],
  ["F", 46.947332, 7.436124, "hgN", side("N", "Laupenstrasse")],
];
for (const [label, lat, lon, node, sd] of hg) q("hirsch", label, lat, lon, { noun: "bay", access: "autonomous", nodes: [node], side: sd });
q("schanz", "", 46.947942, 7.437114, { key: "1", nodes: ["sch"], access: "autonomous" });
q("schanz", "", 46.947933, 7.437284, { key: "2", nodes: ["sch"], access: "autonomous" });

// ---------------------------------------------------------------- street stops

/**
 * A street stop with two unsigned edges, one per direction.
 * @param {string} key @param {string} didok @param {string} name @param {number} lat @param {number} lon
 * @param {{ street?: string, axis?: "EW" | "NS", of?: QuaySide["of"], node?: string, precision?: Quay["precision"], access?: Quay["access"], labels?: [string, string] }} [o]
 */
function street(key, didok, name, lat, lon, o = {}) {
  st(key, didok, name, lat, lon);
  const axis = o.axis ?? "EW";
  const d = 0.00009;
  const precision = o.precision ?? "edge";
  const off = precision === "edge" ? d : 0;
  const nodes = o.node ? [o.node] : undefined;
  // "a" serves the forward direction of the lines defined below, "b" the way back
  q(key, o.labels?.[0] ?? "", lat - (axis === "EW" ? off : 0), lon + (axis === "NS" ? off : 0), {
    key: "a",
    precision,
    nodes,
    access: o.access ?? "autonomous",
    side: precision === "station" ? undefined : side(axis === "EW" ? "S" : "E", o.street ?? "", o.of),
  });
  q(key, o.labels?.[1] ?? "", lat + (axis === "EW" ? off : 0), lon - (axis === "NS" ? off : 0), {
    key: "b",
    precision,
    nodes,
    access: o.access ?? "autonomous",
    side: precision === "station" ? undefined : side(axis === "EW" ? "N" : "W", o.street ?? "", o.of),
  });
}

street("baeren", "8507151", "Bern, Bärenplatz", 46.9479, 7.44415, { street: "Spitalgasse", of: "tram-track", node: "bar" });
street("zyt", "8507152", "Bern, Zytglogge", 46.94795, 7.4477, { street: "Marktgasse", of: "tram-track", node: "zyt" });
street("bundes", "8589113", "Bern, Bundesplatz", 46.9469, 7.4435, { street: "Bundesgasse", node: "bund" });
street("rathaus", "8507153", "Bern, Rathaus", 46.9486, 7.4519, { street: "Kramgasse" });
street("nydegg", "8507154", "Bern, Nydegg", 46.9485, 7.4564, { street: "Nydeggbrücke" });
street("baerenpark", "8507155", "Bern, Bärenpark", 46.9479, 7.4596, { street: "Grosser Muristalden" });
street("zpk", "8507156", "Bern, Zentrum Paul Klee", 46.9493, 7.4733, { street: "Monument im Fruchtland", precision: "edge-at-station" });
street("kursaal", "8507160", "Bern, Kursaal", 46.9534, 7.4487, { street: "Kornhausstrasse", axis: "NS", of: "tram-track" });
street("viktoria", "8507161", "Bern, Viktoriaplatz", 46.9556, 7.4502, { street: "Viktoriaplatz", axis: "NS" });
street("breitenrain", "8507162", "Bern, Breitenrain", 46.959, 7.4542, { street: "Breitenrainplatz", of: "tram-track" });
street("guisan", "8507163", "Bern, Guisanplatz Expo", 46.9608, 7.4648, { street: "Papiermühlestrasse", axis: "NS", of: "tram-track" });
street("wankdorfbhf", "8507164", "Bern Wankdorf, Bahnhof", 46.9677, 7.4654, { street: "Wankdorfallee", labels: ["A", "B"] });
street("helvetia", "8507170", "Bern, Helvetiaplatz", 46.9436, 7.4496, { street: "Helvetiaplatz", axis: "NS", of: "tram-track" });
street("monbijou", "8507171", "Bern, Monbijou", 46.9427, 7.436, { street: "Monbijoustrasse", axis: "NS", of: "tram-track" });
street("kocher", "8507172", "Bern, Kocherpark", 46.9453, 7.434, { street: "Effingerstrasse", of: "tram-track" });
street("sulgenau", "8507173", "Bern, Sulgenau", 46.9393, 7.438, { street: "Monbijoustrasse", axis: "NS", of: "tram-track" });
street("gurtenbahn", "8507174", "Wabern, Gurtenbahn", 46.9285, 7.444, { street: "Seftigenstrasse", of: "tram-track" });
street("wabern", "8507175", "Wabern, Tram-Endstation", 46.9265, 7.451, { street: "Seftigenstrasse", of: "tram-track", precision: "station" });
street("eiger", "8507176", "Bern, Eigerplatz", 46.9406, 7.4312, { street: "Eigerplatz", axis: "NS" });
street("koenizschloss", "8507177", "Köniz, Schloss", 46.9243, 7.4145, { street: "Schwarzenburgstrasse", axis: "NS" });
street("schliern", "8507178", "Köniz Schliern", 46.9119, 7.4131, { street: "Muhlernstrasse", axis: "NS", precision: "edge-at-station" });
street("rosengarten", "8507180", "Bern, Rosengarten", 46.9517, 7.4608, { street: "Laubeggstrasse", axis: "NS" });
street("ostermbhf", "8507181", "Ostermundigen, Bahnhof", 46.9556, 7.484, { street: "Bernstrasse" });
street("zollgasse", "8507182", "Ostermundigen, Zollgasse", 46.9566, 7.487, { street: "Bernstrasse" });
street("rueti", "8507183", "Ostermundigen, Rüti", 46.953, 7.501, { street: "Rütiweg", precision: "edge-at-station" });
street("uni", "8507184", "Bern, Universität", 46.9506, 7.4375, { street: "Länggassstrasse", axis: "NS" });
street("laengg", "8507185", "Bern, Länggasse", 46.9542, 7.4294, { street: "Länggassstrasse", axis: "NS", precision: "edge-at-station" });
street("bollwerk", "8507186", "Bern, Bollwerk", 46.9503, 7.4406, { street: "Bollwerk", axis: "NS" });
street("lorraine", "8507187", "Bern, Lorraine", 46.9573, 7.4447, { street: "Lorrainestrasse", axis: "NS" });
street("kv", "8507188", "Bern, Kaufmännischer Verband", 46.9462, 7.4333, { street: "Effingerstrasse", of: "tram-track" });
street("lory", "8507189", "Bern, Loryplatz", 46.9435, 7.4215, { street: "Schlossstrasse", of: "tram-track" });
street("fischer", "8507190", "Bern, Fischermätteli", 46.9388, 7.4186, { street: "Weissensteinstrasse", of: "tram-track", precision: "edge-at-station" });
street("thunplatz", "8507191", "Bern, Thunplatz", 46.9409, 7.4563, { street: "Thunstrasse", of: "tram-track" });
street("ostring", "8507192", "Bern, Ostring", 46.9423, 7.4745, { street: "Ostring", of: "tram-track" });
street("muri", "8507193", "Muri b. Bern", 46.9316, 7.4868, { street: "Thunstrasse", of: "tram-track" });
street("guemligen", "8507194", "Gümligen, Bahnhof", 46.9343, 7.5092, { street: "Worbstrasse", of: "tram-track" });
street("worb", "8507195", "Worb Dorf", 46.9296, 7.5633, { street: "Bahnhofstrasse", of: "tram-track", precision: "edge-at-station" });
street("buempliz", "8507196", "Bern Bümpliz, Post", 46.9415, 7.392, { street: "Bümplizstrasse", of: "tram-track" });
street("bruennen", "8507197", "Bern Brünnen Westside, Bahnhof", 46.944, 7.374, { street: "Riedbachstrasse", of: "tram-track", precision: "edge-at-station" });
street("saali", "8507198", "Bern, Saali", 46.9357, 7.4772, { street: "Saalistrasse", of: "tram-track", precision: "station" });
street("hinterk", "8507199", "Hinterkappelen, Bernstrasse", 46.967, 7.379, { street: "Bernstrasse", precision: "station" });
street("bremg", "8507200", "Bremgarten BE, Kalchacker", 46.977, 7.44, { street: "Kalchackerstrasse", axis: "NS", precision: "edge-at-station" });

// ---------------------------------------------------------------- rail stations elsewhere

/**
 * @param {string} key @param {string} didok @param {string} name @param {number} lat @param {number} lon @param {string[]} tracks
 * @param {number} [level]
 */
function rail(key, didok, name, lat, lon, tracks, level) {
  if (!stations[key]) st(key, didok, name, lat, lon);
  tracks.forEach((t, i) => {
    q(key, t, lat + (i - tracks.length / 2) * 0.00007, lon + (i % 2) * 0.00012, {
      noun: "track",
      access: "autonomous",
      precision: tracks.length > 4 ? "edge" : "edge-at-station",
      ...(level === undefined ? {} : { level }),
    });
  });
}
rail("zurich", "8503000", "Zürich HB", 47.3779, 8.5403, ["3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18"]);
rail("zurich", "8503000", "Zürich HB", 47.3786, 8.5392, ["31", "32", "33", "34"], -2);
rail("wankdorf", "8516161", "Bern Wankdorf", 46.9676, 7.4652, ["1", "2", "3", "4"]);
rail("zollikofen", "8504410", "Zollikofen", 46.996, 7.4572, ["1", "2"]);
rail("burgdorf", "8508005", "Burgdorf", 47.0607, 7.6217, ["1", "2", "3"]);
rail("olten", "8500218", "Olten", 47.3519, 7.9077, ["4", "7", "8", "9", "10", "11", "12"]);
rail("aarau", "8502113", "Aarau", 47.3913, 8.0513, ["3", "4", "5", "6"]);
rail("flughafen", "8503016", "Zürich Flughafen", 47.4503, 8.5624, ["1", "2", "3", "4"], -2);
rail("winterthur", "8506000", "Winterthur", 47.5003, 8.7237, ["3", "4", "5", "6", "7"]);
rail("stgallen", "8506302", "St. Gallen", 47.4233, 9.3697, ["1", "2", "3", "4"]);
rail("fribourg", "8504100", "Fribourg/Freiburg", 46.8031, 7.151, ["1", "2", "3"]);
rail("lausanne", "8501120", "Lausanne", 46.5168, 6.6291, ["1", "3", "5", "7", "8"]);
rail("geneve", "8501008", "Genève", 46.2102, 6.1424, ["3", "4", "5", "6", "7"]);
rail("muensingen", "8507006", "Münsingen", 46.8743, 7.5633, ["1", "2"]);
rail("thun", "8507100", "Thun", 46.7549, 7.6296, ["1", "2", "3", "4"]);
rail("spiez", "8507483", "Spiez", 46.6864, 7.6801, ["1", "2", "3"]);
rail("interlakenw", "8507493", "Interlaken West", 46.6826, 7.8515, ["1", "2"]);
rail("interlakeno", "8507492", "Interlaken Ost", 46.6905, 7.869, ["5", "6", "7"]);
rail("visp", "8501605", "Visp", 46.294, 7.8815, ["4", "5", "6"]);
rail("brig", "8501609", "Brig", 46.3194, 7.988, ["1", "2", "3"]);
rail("belp", "8507082", "Belp", 46.8904, 7.4979, ["1", "2"]);
rail("biel", "8504300", "Biel/Bienne", 47.1329, 7.2429, ["1", "3", "5", "7"]);
rail("lyss", "8504414", "Lyss", 47.0741, 7.3066, ["1", "2", "3"]);
rail("basel", "8500010", "Basel SBB", 47.5474, 7.5896, ["4", "5", "6", "7", "8", "9"]);
rail("liestal", "8500023", "Liestal", 47.4844, 7.7314, ["1", "2", "3"]);
rail("luzern", "8505000", "Luzern", 47.0502, 8.3102, ["3", "4", "5", "6", "7"]);
rail("solothurn", "8500207", "Solothurn", 47.2044, 7.5429, ["21", "22"]);
rail("jegenstorf", "8508061", "Jegenstorf", 47.0486, 7.5078, ["1", "2"]);
rail("worblaufen", "8507077", "Worblaufen", 46.979, 7.4589, ["1", "2", "3", "4"]);
rail("bolligen", "8507078", "Bolligen", 46.9752, 7.4968, ["1", "2"]);
rail("europaplatz", "8504489", "Bern Europaplatz", 46.9433, 7.4063, ["1", "2"]);

// Zürich trams
street("zhbq", "8587349", "Zürich, Bahnhofquai/HB", 47.3771, 8.5418, { street: "Bahnhofquai", axis: "NS", of: "tram-track", labels: ["A", "B"] });
street("zhbs", "8587348", "Zürich, Bahnhofstrasse/HB", 47.3767, 8.5395, { street: "Bahnhofstrasse", axis: "NS", of: "tram-track" });
street("rennweg", "8591316", "Zürich, Rennweg", 47.3732, 8.5387, { street: "Bahnhofstrasse", axis: "NS", of: "tram-track" });
street("parade", "8591299", "Zürich, Paradeplatz", 47.3697, 8.5389, { street: "Bahnhofstrasse", axis: "NS", of: "tram-track" });
street("bellevue", "8591058", "Zürich, Bellevue", 47.367, 8.545, { street: "Bellevueplatz", of: "tram-track" });
street("stampf", "8591379", "Zürich, Stampfenbachplatz", 47.3792, 8.5437, { street: "Stampfenbachstrasse", axis: "NS", of: "tram-track" });
street("oerlikon", "8591063", "Zürich Oerlikon, Bahnhof", 47.4115, 8.5441, { street: "Hofwiesenstrasse", axis: "NS", of: "tram-track", precision: "edge-at-station" });

// Boats on Lake Thun
st("thunsee", "8507150", "Thun (See)", 46.7541, 7.6312);
q("thunsee", "1", 46.7541, 7.6312, { noun: "pier", access: "assisted" });
st("huenibach", "8508369", "Hünibach (See)", 46.7446, 7.6497);
q("huenibach", "", 46.7446, 7.6497, { noun: "pier", key: "1", precision: "station", access: "assisted" });
st("oberhofen", "8508372", "Oberhofen am Thunersee (See)", 46.7296, 7.6689);
q("oberhofen", "", 46.7296, 7.6689, { noun: "pier", key: "1", precision: "station", access: "assisted" });
st("spiezsee", "8508378", "Spiez Schiffstation", 46.6913, 7.6889);
q("spiezsee", "", 46.6913, 7.6889, { noun: "pier", key: "1", precision: "station", access: "assisted-on-notice" });

// ---------------------------------------------------------------- lines

/**
 * @typedef {Object} LineDef
 * @property {string} id
 * @property {LineBadge} badge
 * @property {number} headwayS
 * @property {number} offsetS
 * @property {"observed" | "predicted" | "timetable"} live
 * @property {{ station: string, quay: [string, string], t: number }[]} stops  t = seconds from the first stop
 * @property {string} [sectors]
 * @property {string} [number]
 * @property {number} [firstS]  first departure of the day (seconds after midnight)
 * @property {number} [lastS]
 */

/** @type {LineDef[]} */
export const lines = [];

const OP = { bm: "Bernmobil", sbb: "SBB", bls: "BLS", rbs: "RBS", pa: "PostAuto", vbz: "VBZ", blsS: "BLS Schifffahrt" };

/**
 * @param {string} name @param {string} category @param {Mode} mode @param {string} operator
 * @param {number} headwayMin @param {number} offsetMin
 * @param {[string, string | [string, string], number][]} stops  [stationKey, quay key (or [fwd, back]), minutes from start]
 * @param {Partial<LineDef>} [extra]
 */
function line(name, category, mode, operator, headwayMin, offsetMin, stops, extra = {}) {
  lines.push({
    id: (category + name).replace(/[^A-Za-z0-9]/g, "") + "-" + lines.length,
    badge: { name, category, mode, operator },
    headwayS: headwayMin * 60,
    offsetS: offsetMin * 60,
    live: mode === "rail" ? "predicted" : operator === OP.pa || mode === "boat" ? "timetable" : "observed",
    stops: stops.map(([station, quay, t]) => ({ station, quay: typeof quay === "string" ? [quay, quay] : quay, t: t * 60 })),
    ...extra,
  });
}
/** street-stop default: forward uses edge "a", back uses "b" @type {[string, string]} */
const AB = ["a", "b"];

line("9", "T", "tram", OP.bm, 6, 1, [
  ["wabern", AB, 0], ["gurtenbahn", AB, 2], ["sulgenau", AB, 6], ["monbijou", AB, 8], ["hirsch", ["B", "A"], 10],
  ["bernbhf", ["B", "C"], 12], ["baeren", AB, 14], ["zyt", AB, 16], ["kursaal", AB, 19], ["viktoria", AB, 20],
  ["breitenrain", AB, 22], ["guisan", AB, 25], ["wankdorfbhf", AB, 28],
]);
line("6", "T", "tram", OP.bm, 10, 3, [
  ["fischer", AB, 0], ["lory", AB, 3], ["kv", AB, 6], ["kocher", AB, 7], ["hirsch", ["B", "A"], 9], ["bernbhf", ["B", "C"], 11],
  ["baeren", AB, 13], ["zyt", AB, 15], ["helvetia", AB, 18], ["thunplatz", AB, 21], ["muri", AB, 28], ["guemligen", AB, 33], ["worb", AB, 44],
]);
line("7", "T", "tram", OP.bm, 7.5, 2, [
  ["buempliz", AB, 0], ["lory", AB, 7], ["kv", AB, 10], ["kocher", AB, 11], ["hirsch", ["B", "A"], 13], ["bernbhf", ["A", "D"], 15],
  ["baeren", AB, 17], ["zyt", AB, 19], ["helvetia", AB, 22], ["thunplatz", AB, 25], ["ostring", AB, 30],
]);
line("8", "T", "tram", OP.bm, 7.5, 5, [
  ["bruennen", AB, 0], ["buempliz", AB, 5], ["lory", AB, 12], ["kv", AB, 15], ["kocher", AB, 16], ["hirsch", ["B", "A"], 18],
  ["bernbhf", ["B", "C"], 20], ["baeren", AB, 22], ["zyt", AB, 24], ["helvetia", AB, 27], ["thunplatz", AB, 30], ["saali", AB, 37],
]);
line("10", "B", "bus", OP.bm, 5, 0, [
  ["schliern", AB, 0], ["koenizschloss", AB, 5], ["eiger", AB, 11], ["monbijou", AB, 13], ["hirsch", ["C", "D"], 16],
  ["bernbhf", ["L", "I"], 18], ["zyt", AB, 21], ["kursaal", AB, 24], ["viktoria", AB, 25], ["rosengarten", AB, 29],
  ["ostermbhf", AB, 34], ["zollgasse", AB, 36], ["rueti", AB, 40],
]);
line("12", "B", "bus", OP.bm, 6, 4, [
  ["laengg", AB, 0], ["uni", AB, 3], ["hirsch", ["E", "F"], 5], ["bernbhf", ["A", "D"], 7], ["baeren", AB, 9], ["zyt", AB, 11],
  ["rathaus", AB, 13], ["nydegg", AB, 15], ["baerenpark", AB, 16], ["zpk", AB, 21],
]);
line("19", "B", "bus", OP.bm, 10, 6, [
  ["bernbhf", ["K1", "M"], 0], ["bundes", AB, 2], ["helvetia", AB, 6], ["thunplatz", AB, 9], ["ostring", AB, 14],
]);
line("20", "B", "bus", OP.bm, 5, 2, [
  ["bernbhf", ["E", "F"], 0], ["bollwerk", AB, 2], ["lorraine", AB, 5], ["breitenrain", AB, 8], ["wankdorfbhf", AB, 13],
]);
line("21", "B", "bus", OP.bm, 15, 7, [["bernbhf", ["H", "H"], 0], ["bollwerk", AB, 2], ["bremg", AB, 14]]);
line("101", "B", "bus", OP.pa, 15, 9, [["bernpost", ["S", "Y"], 0], ["schanz", ["1", "2"], 2], ["hinterk", AB, 17]]);
line("N17", "B", "bus", OP.bm, 30, 12, [["bernbhf", ["G", "G"], 0], ["baeren", AB, 2], ["zyt", AB, 4], ["helvetia", AB, 7], ["muri", AB, 16]], {
  firstS: 0,
  lastS: 4 * 3600,
});

line("IC 1", "IC", "rail", OP.sbb, 60, 2, [
  ["geneve", ["4", "5"], 0], ["lausanne", ["5", "7"], 36], ["fribourg", ["2", "1"], 80], ["bern", ["7", "6"], 104],
  ["zurich", ["32", "33"], 160], ["flughafen", ["3", "2"], 172], ["winterthur", ["5", "4"], 187], ["stgallen", ["2", "1"], 223],
], { sectors: "A-D", number: "7" });
line("IC 8", "IC", "rail", OP.sbb, 60, 6, [
  ["brig", ["2", "1"], 0], ["visp", ["5", "4"], 8], ["spiez", ["2", "1"], 35], ["thun", ["2", "1"], 45], ["bern", ["8", "5"], 64],
  ["olten", ["7", "8"], 91], ["zurich", ["33", "31"], 122],
], { sectors: "A-C", number: "8" });
line("IC 61", "IC", "rail", OP.sbb, 60, 34, [
  ["interlakeno", ["6", "5"], 0], ["interlakenw", ["1", "2"], 5], ["spiez", ["3", "1"], 22], ["thun", ["3", "1"], 32], ["bern", ["6", "7"], 51],
  ["olten", ["10", "9"], 78], ["liestal", ["2", "1"], 96], ["basel", ["8", "6"], 107],
], { sectors: "B-D", number: "9" });
line("IR 15", "IR", "rail", OP.sbb, 60, 36, [
  ["lausanne", ["3", "1"], 0], ["fribourg", ["3", "1"], 45], ["bern", ["5", "4"], 68], ["zollikofen", ["1", "2"], 75], ["burgdorf", ["2", "1"], 88],
  ["olten", ["8", "7"], 115], ["aarau", ["4", "3"], 125], ["zurich", ["12", "13"], 152],
], { sectors: "A-C", number: "25" });
line("IR 17", "IR", "rail", OP.sbb, 60, 17, [
  ["bern", ["9", "9"], 0], ["zollikofen", ["1", "2"], 7], ["burgdorf", ["3", "1"], 18], ["olten", ["11", "12"], 44], ["luzern", ["5", "6"], 80],
], { number: "24" });
line("S1", "S", "rail", OP.bls, 30, 9, [
  ["fribourg", ["1", "2"], 0], ["europaplatz", ["1", "2"], 26], ["bern", ["3", "2"], 31], ["wankdorf", ["2", "3"], 36], ["muensingen", ["1", "2"], 47], ["thun", ["4", "4"], 62],
], { sectors: "B-C" });
line("S3", "S", "rail", OP.bls, 30, 21, [
  ["biel", ["3", "5"], 0], ["lyss", ["2", "1"], 12], ["zollikofen", ["2", "1"], 27], ["wankdorf", ["1", "4"], 31], ["bern", ["10", "12"], 36], ["europaplatz", ["2", "1"], 40], ["belp", ["1", "2"], 54],
], { sectors: "B-C" });
line("S7", "S", "rail", OP.rbs, 15, 3, [
  ["bern", ["24", "24"], 0], ["worblaufen", ["3", "4"], 6], ["bolligen", ["1", "2"], 12], ["worb", ["a", "b"], 24],
]);
line("RE 5", "RE", "rail", OP.rbs, 30, 8, [
  ["bern", ["21", "22"], 0], ["worblaufen", ["1", "2"], 5], ["jegenstorf", ["1", "2"], 15], ["solothurn", ["21", "22"], 37],
]);

line("11", "T", "tram", OP.vbz, 7.5, 1, [
  ["bellevue", AB, 0], ["parade", AB, 4], ["rennweg", AB, 6], ["zhbs", AB, 8], ["zhbq", AB, 10], ["stampf", AB, 12], ["oerlikon", AB, 25],
]);
line("BAT 31", "BAT", "boat", OP.blsS, 120, 40, [
  ["thunsee", ["1", "1"], 0], ["huenibach", ["1", "1"], 10], ["oberhofen", ["1", "1"], 22], ["spiezsee", ["1", "1"], 48],
], { firstS: 9 * 3600, lastS: 18 * 3600, number: "31" });

// modes per quay / station from the lines that call there
for (const l of lines) {
  for (const s of l.stops) {
    const stn = stations[s.station];
    if (!stn) throw new Error("line " + l.badge.name + ": unknown station " + s.station);
    if (!stn.modes.includes(l.badge.mode)) stn.modes.push(l.badge.mode);
    for (const key of s.quay) {
      const quay = quaysById[`${stn.didok}:0:${key}`];
      if (!quay) throw new Error(`line ${l.badge.name}: unknown quay ${s.station}/${key}`);
      if (!quay.modes.includes(l.badge.mode)) quay.modes.push(l.badge.mode);
    }
  }
}
const modeRank = ["rail", "metro", "tram", "bus", "boat"];
for (const s of Object.values(stations)) {
  s.modes.sort((a, b) => modeRank.indexOf(a) - modeRank.indexOf(b));
  for (const quay of s.quays) {
    if (!quay.modes.length) quay.modes = s.quays[0].noun === "track" ? ["rail"] : quay.noun === "pier" ? ["boat"] : ["bus"];
  }
}

// ---------------------------------------------------------------- addresses and POIs

/** @type {Place[]} */
export const places = [
  { id: "addr:1", kind: "address", name: "Bundesgasse 3", detail: "3011 Bern", lat: 46.9466, lon: 7.4442 },
  { id: "addr:2", kind: "address", name: "Kramgasse 49", detail: "3011 Bern", lat: 46.9479, lon: 7.4506 },
  { id: "addr:3", kind: "address", name: "Länggassstrasse 51", detail: "3012 Bern", lat: 46.9531, lon: 7.4321 },
  { id: "addr:4", kind: "address", name: "Marktgasse 12", detail: "3011 Bern", lat: 46.94795, lon: 7.4462 },
  { id: "addr:5", kind: "address", name: "Bahnhofstrasse 1", detail: "8001 Zürich", lat: 47.3673, lon: 8.5398 },
  { id: "addr:6", kind: "address", name: "Monbijoustrasse 61", detail: "3007 Bern", lat: 46.9409, lon: 7.4369 },
  { id: "addr:7", kind: "address", name: "Papiermühlestrasse 71", detail: "3014 Bern", lat: 46.9626, lon: 7.4649 },
  { id: "poi:1", kind: "poi", name: "Bundeshaus", detail: "Parliament · Bern", lat: 46.94653, lon: 7.44433 },
  { id: "poi:2", kind: "poi", name: "Zentrum Paul Klee", detail: "Museum · Bern", lat: 46.9489, lon: 7.4741 },
  { id: "poi:3", kind: "poi", name: "BärenPark", detail: "Attraction · Bern", lat: 46.9479, lon: 7.4597 },
  { id: "poi:4", kind: "poi", name: "Universität Bern, Hauptgebäude", detail: "University · Bern", lat: 46.95046, lon: 7.4381 },
  { id: "poi:5", kind: "poi", name: "Berner Münster", detail: "Church · Bern", lat: 46.9472, lon: 7.4512 },
  { id: "poi:6", kind: "poi", name: "Rosengarten", detail: "Park · Bern", lat: 46.9515, lon: 7.4604 },
  { id: "poi:7", kind: "poi", name: "Inselspital", detail: "Hospital · Bern", lat: 46.9475, lon: 7.4252 },
  { id: "poi:8", kind: "poi", name: "Kunsthaus Zürich", detail: "Museum · Zürich", lat: 47.3703, lon: 8.5481 },
  { id: "poi:9", kind: "poi", name: "Stadion Wankdorf", detail: "Stadium · Bern", lat: 46.9632, lon: 7.4649 },
];

// ---------------------------------------------------------------- walking network (Bern station area)

/** @typedef {{ id: string, lat: number, lon: number, level: number | null }} WNode */
/**
 * @typedef {Object} WEdge
 * @property {string} a
 * @property {string} b
 * @property {IndoorFeatureProps["kind"]} kind
 * @property {string} name
 * @property {number} [steps]  number of stair steps (kind "steps")
 * @property {number} [lenM]   override of the geometric length
 * @property {boolean} [indoor]
 * @property {[number, number][]} [via]  intermediate [lon, lat] vertices from a to b
 */

/** @type {Record<string, WNode>} */
export const wnodes = {};
/** @type {WEdge[]} */
export const wedges = [];

/** @param {string} id @param {number} lat @param {number} lon @param {number | null} [level] */
function n(id, lat, lon, level = null) {
  wnodes[id] = { id, lat, lon, level };
}
/** @param {string} a @param {string} b @param {WEdge["kind"]} kind @param {string} [name] @param {Partial<WEdge>} [o] */
function e(a, b, kind, name = "", o = {}) {
  if (!wnodes[a] || !wnodes[b]) throw new Error("edge " + a + "-" + b);
  wedges.push({ a, b, kind, name, ...o });
}

// streets (outdoors: level unknown)
n("bhp", 46.94822, 7.44005);
n("bhpN", 46.94868, 7.44035);
n("bol", 46.94905, 7.4404);
n("bald", 46.94762, 7.44035);
n("baldE", 46.94752, 7.4409);
n("bubW", 46.94745, 7.4394);
n("bubS", 46.94728, 7.4406);
n("chr", 46.94685, 7.4409);
n("hgN", 46.947, 7.438);
n("hgS", 46.9461, 7.4379);
n("sch", 46.94795, 7.4372, 1);
n("spi", 46.94775, 7.4425);
n("bar", 46.94785, 7.4441);
n("mkt", 46.94792, 7.4459);
n("zyt", 46.94797, 7.4477);
n("krm", 46.948, 7.45);
n("bund", 46.947, 7.4439);
n("bgs", 46.94655, 7.442);
n("korn", 46.9487, 7.4478);
e("bhp", "bhpN", "sidewalk", "Bahnhofplatz");
e("bhpN", "bol", "sidewalk", "Bollwerk");
e("bhp", "bald", "crossing", "Bahnhofplatz");
e("bald", "baldE", "pedestrian", "Bubenbergplatz");
e("bald", "bubW", "sidewalk", "Bubenbergplatz");
e("bald", "bubS", "crossing", "Bubenbergplatz");
e("bubS", "chr", "sidewalk", "Christoffelgasse");
e("bubW", "hgN", "sidewalk", "Hirschengraben");
e("hgN", "hgS", "footway", "Hirschengraben");
e("bubW", "sch", "sidewalk", "Schanzenstrasse");
e("baldE", "spi", "pedestrian", "Spitalgasse");
e("spi", "bar", "pedestrian", "Spitalgasse");
e("bar", "mkt", "pedestrian", "Marktgasse");
e("mkt", "zyt", "pedestrian", "Marktgasse");
e("zyt", "krm", "pedestrian", "Kramgasse");
e("zyt", "korn", "sidewalk", "Kornhausplatz");
e("bar", "bund", "pedestrian", "Bärenplatz");
e("bund", "bgs", "sidewalk", "Bundesgasse");
e("bgs", "chr", "sidewalk", "Bundesgasse");
e("hgS", "bgs", "sidewalk", "Bundesgasse");

// station hall (0) and lower concourse (−1)
n("hall", 46.9485, 7.43965, 0);
n("uh", 46.94853, 7.43925, -1);
e("bhp", "hall", "footway", "Main entrance", { indoor: true });
e("hall", "uh", "steps", "", { steps: 24, indoor: true, via: [[7.43952, 46.94846]] });
e("hall", "uh", "escalator", "", { indoor: true, lenM: 14 });
e("hall", "uh", "lift", "", { indoor: true, via: [[7.43946, 46.94858]] });

// Christoffelunterführung (−1) to Bubenbergplatz and Christoffelgasse
n("chrU1", 46.948, 7.43975, -1);
n("chrU2", 46.94755, 7.4402, -1);
n("chrU3", 46.947, 7.4407, -1);
e("uh", "chrU1", "corridor", "Christoffelunterführung", { indoor: true });
e("chrU1", "chrU2", "corridor", "Christoffelunterführung", { indoor: true });
e("chrU2", "chrU3", "corridor", "Christoffelunterführung", { indoor: true });
e("chrU1", "bhp", "steps", "", { steps: 18, indoor: true });
e("chrU2", "bald", "steps", "", { steps: 22, indoor: true, via: [[7.44024, 46.9476]] });
e("chrU2", "bald", "lift", "", { indoor: true, via: [[7.44032, 46.94754]] });
e("chrU3", "chr", "steps", "", { steps: 20, indoor: true });
e("chrU3", "chr", "escalator", "", { indoor: true, lenM: 12, via: [[7.44082, 46.9469]] });

// Neuengassunterführung (−1) to Bollwerk and the RBS station (−2)
n("neuU", 46.94885, 7.44, -1);
n("rbsC", 46.94935, 7.43975, -2);
n("rbs12", 46.94958, 7.43986, -2);
n("rbs34", 46.94948, 7.43982, -2);
e("uh", "neuU", "corridor", "Neuengassunterführung", { indoor: true, via: [[7.4396, 46.94872]] });
e("neuU", "bol", "steps", "", { steps: 20, indoor: true });
e("neuU", "bol", "lift", "", { indoor: true, via: [[7.4403, 46.94893]] });
e("neuU", "rbsC", "steps", "", { steps: 28, indoor: true });
e("neuU", "rbsC", "escalator", "", { indoor: true, lenM: 16, via: [[7.43992, 46.94912]] });
e("neuU", "rbsC", "lift", "", { indoor: true, via: [[7.4398, 46.94906]] });
e("rbsC", "rbs34", "platform", "Platform 23/24", { indoor: true });
e("rbsC", "rbs12", "platform", "Platform 21/22", { indoor: true });

// main underpass (−1) below the SBB platforms, and the Welle footbridge (+1) at their west end
n("up0", 46.94858, 7.4388, -1);
n("w0", 46.948, 7.437, 1);
/** @type {[string, number, number, number, number][]} id, underpass lat/lon, welle lat/lon */
const plats = [
  ["12", 46.94868, 7.43872, 46.94822, 7.4369],
  ["34", 46.9488, 7.43866, 46.94835, 7.43686],
  ["56", 46.94893, 7.4386, 46.94848, 7.43681],
  ["78", 46.94906, 7.43854, 46.9486, 7.43672],
  ["910", 46.9492, 7.43848, 46.9488, 7.43668],
  ["1213", 46.94934, 7.43842, 46.94895, 7.4366],
];
function platName(/** @type {string} */ id) {
  return "Platform " + (id.length === 2 ? id[0] + "/" + id[1] : id === "910" ? "9/10" : "12/13");
}
let prevU = "up0";
let prevW = "w0";
for (const [id, ulat, ulon, wlat, wlon] of plats) {
  n("u" + id, ulat, ulon, -1);
  n("p" + id, ulat - 0.00003, ulon - 0.00022, 0);
  n("w" + id, wlat, wlon, 1);
  n("pw" + id, wlat + 0.00003, wlon + 0.00022, 0);
}
e("uh", "up0", "corridor", "Station underpass", { indoor: true });
e("hall", "p12", "footway", "Platform 1 access", { indoor: true, via: [[7.4392, 46.94868]] });
e("sch", "w0", "footway", "Welle");
for (const [id] of plats) {
  const name = platName(id);
  e(prevU, "u" + id, "corridor", "Station underpass", { indoor: true });
  e("u" + id, "p" + id, "steps", "", { steps: 26, indoor: true });
  // ramp: a footway that connects two levels
  e("u" + id, "p" + id, "footway", "", { indoor: true, lenM: 48, via: [[wnodes["u" + id].lon - 0.00016, wnodes["u" + id].lat + 0.00005]] });
  if (id === "56" || id === "78") e("u" + id, "p" + id, "lift", "", { indoor: true, via: [[wnodes["u" + id].lon - 0.00008, wnodes["u" + id].lat - 0.00005]] });
  e("p" + id, "pw" + id, "platform", name);
  e(prevW, "w" + id, "corridor", "Welle", { indoor: true });
  e("w" + id, "pw" + id, "steps", "", { steps: 30 });
  e("w" + id, "pw" + id, "lift", "", { via: [[wnodes["w" + id].lon + 0.0001, wnodes["w" + id].lat + 0.00005]] });
  prevU = "u" + id;
  prevW = "w" + id;
}
// far platform 49/50, reached over the level-1 footbridge
n("p4950", 46.94826, 7.43345, 0);
n("w49", 46.94838, 7.4342, 1);
e("w78", "w49", "corridor", "Footbridge to tracks 49/50", { indoor: false });
e("w49", "p4950", "steps", "", { steps: 26 });
e("w49", "p4950", "lift", "", { via: [[7.4338, 46.94836]] });

// PostAuto deck (+2) above the tracks
n("deck", 46.94893, 7.4385, 2);
n("deckW", 46.9487, 7.4376, 2);
e("deck", "deckW", "footway", "Postautostation", {});
e("deck", "u56", "lift", "", { indoor: true, via: [[7.43868, 46.94898]] });
e("deck", "p56", "steps", "", { steps: 44 });
e("deckW", "sch", "footway", "Schanzenstrasse", { lenM: 95 });

/** Nodes a traveller on the street can be snapped to. */
export const streetNodes = Object.values(wnodes).filter((x) => x.level === null).map((x) => x.id);
