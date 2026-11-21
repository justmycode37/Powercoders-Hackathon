// Sample community events for immigrants, refugees and marginalised groups.
// NOTE: this is generated demo data, not real events. Replace `generateEvents` with a real feed later.
(function () {
  const CATEGORIES = {
    language:  { color: '#5856d6', label: 'Language' },
    food:      { color: '#ff9500', label: 'Community meal' },
    legal:     { color: '#007aff', label: 'Advice' },
    jobs:      { color: '#30b0c7', label: 'Work & training' },
    community: { color: '#ff2d55', label: 'Meetup' },
    sport:     { color: '#34c759', label: 'Sport' },
    kids:      { color: '#e6a800', label: 'Kids & learning' },
    health:    { color: '#ff3b30', label: 'Health' },
  };

  // Stroke glyphs on a 24×24 grid, drawn white on the coloured circle
  const GLYPHS = {
    language:  'M5 5h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8l-4 3.5V17H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z',
    food:      'M7 3v7a2 2 0 0 0 4 0V3M9 10v11M16 21V3c-2 1.5-3 4-3 7h3',
    legal:     'M12 4v16M7 20h10M5 7h14M5 7l-2.5 6a2.5 2.5 0 0 0 5 0zM19 7l-2.5 6a2.5 2.5 0 0 0 5 0z',
    jobs:      'M4 8h16v11H4zM9 8V5.5h6V8M4 13h16',
    community: 'M12 20s-7.5-4.6-7.5-10.2A4.2 4.2 0 0 1 12 7.3a4.2 4.2 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z',
    sport:     'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18zM12 8l3.8 2.8-1.5 4.5H9.7L8.2 10.8z',
    kids:      'M3 6h6a3 3 0 0 1 3 3v11a2.5 2.5 0 0 0-2.5-2.5H3zM21 6h-6a3 3 0 0 0-3 3v11a2.5 2.5 0 0 1 2.5-2.5H21z',
    health:    'M12 5v14M5 12h14',
  };

  const LANG = { de: 'German', fr: 'French', it: 'Italian' };

  const ABOUT = {
    language: 'Practise everyday conversation in a relaxed group. All levels welcome — volunteers help you with pronunciation, vocabulary and real-life situations like shopping, doctor visits or talking to neighbours.',
    food: 'Come by, eat together and meet people from the neighbourhood. The meal is free and vegetarian options are always available. Feel free to bring friends and family.',
    legal: 'Trained volunteers and lawyers answer your questions confidentially and free of charge. Bring any letters or documents you have. Interpreters can be arranged on request.',
    jobs: 'A practical session to help you take the next step towards work or training in Switzerland. Bring your laptop if you have one — otherwise devices are provided.',
    community: 'A safe and welcoming space to meet others, share experiences and make new friends. No registration needed — just drop in.',
    sport: 'Get moving and have fun together. No experience or equipment needed, and everyone is welcome regardless of level. Water is provided.',
    kids: 'A friendly afternoon for children and parents. Volunteers support with homework, reading and play while parents can connect and ask questions.',
    health: 'Confidential support with health questions from trained professionals. Free of charge and independent of your residence status. Interpreters available.',
  };
  const AUDIENCE = {
    language: 'Newcomers, refugees and anyone learning the local language',
    food: 'Everyone — especially newcomers and people living alone',
    legal: 'Asylum seekers, refugees and migrants',
    jobs: 'Job seekers with a migration background',
    community: 'Migrants, refugees, LGBTQ+ people and allies',
    sport: 'Everyone, all ages and levels',
    kids: 'Families and children',
    health: 'Anyone, regardless of residence status',
  };

  const TITLES = {
    language: [
      (l) => `${l} conversation café`, (l) => `${l} for beginners`, (l) => `${l} A2 practice group`,
      (l) => `Free ${l} lesson`, () => 'Language exchange evening', (l) => `${l} for parents`,
    ],
    food: [
      () => 'Free community dinner', () => 'Cooking together: dishes from home', () => 'Open lunch table',
      () => 'Breakfast meetup', () => 'Free food distribution', () => 'Neighbourhood potluck',
    ],
    legal: [
      () => 'Free asylum law advice', () => 'Residence permit Q&A', () => 'Help with official letters',
      () => 'Tenant rights consultation', () => 'Family reunification info', () => 'Anti-discrimination counselling',
    ],
    jobs: [
      () => 'CV & job application workshop', () => 'Coding taster session', () => 'Diploma recognition info',
      () => 'Interview practice', () => 'Mentoring for job seekers', () => 'Internship info evening',
    ],
    community: [
      () => 'Newcomers meetup', () => 'LGBTQ+ refugee meetup', () => "Women's circle",
      () => 'Intercultural evening', () => 'Open community café', () => 'Music & dance night',
    ],
    sport: [
      () => 'Football for everyone', () => 'Women-only swimming', () => 'Free yoga in the park',
      () => 'Running group', () => 'Volleyball meetup', () => 'Bike repair & ride',
    ],
    kids: [
      () => 'Homework help', () => 'Kids play afternoon', () => 'Reading hour for families',
      () => 'Youth computer club', () => 'Parents & toddlers group', () => 'School system info for parents',
    ],
    health: [
      () => 'Free health consultation', () => 'Mental health support group', () => 'Trauma counselling',
      () => 'Women’s health info', () => 'Vaccination info session', () => 'Health insurance help',
    ],
  };

  const VENUES = ['Community centre', 'Library', 'Neighbourhood hall', 'Youth centre', 'Parish hall', 'Park', 'School', 'Café', 'Sports hall', 'Culture house'];
  const DAYS = ['Today', 'Today', 'Tomorrow', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const TIMES = ['09:00', '10:00', '12:00', '14:00', '15:30', '17:00', '18:00', '18:30', '19:00', '20:00'];

  // [name, lat, lng, number of events, spread in degrees, language]
  const CITIES = [
    ['Zürich', 47.3769, 8.5417, 80, .025, 'de'],
    ['Genève', 46.2044, 6.1432, 60, .02, 'fr'],
    ['Basel', 47.5596, 7.5886, 50, .018, 'de'],
    ['Bern', 46.9480, 7.4474, 60, .018, 'de'],
    ['Lausanne', 46.5197, 6.6323, 45, .016, 'fr'],
    ['Winterthur', 47.4988, 8.7237, 25, .014, 'de'],
    ['Luzern', 47.0502, 8.3093, 30, .014, 'de'],
    ['St. Gallen', 47.4245, 9.3767, 25, .013, 'de'],
    ['Lugano', 46.0037, 8.9511, 25, .012, 'it'],
    ['Biel/Bienne', 47.1368, 7.2468, 25, .012, 'de'],
    ['Thun', 46.7580, 7.6280, 15, .01, 'de'],
    ['Fribourg', 46.8065, 7.1619, 20, .01, 'fr'],
    ['Neuchâtel', 46.9900, 6.9310, 15, .01, 'fr'],
    ['Chur', 46.8508, 9.5320, 15, .01, 'de'],
    ['Sion', 46.2330, 7.3600, 12, .01, 'fr'],
    ['Aarau', 47.3900, 8.0450, 12, .009, 'de'],
    ['Schaffhausen', 47.6970, 8.6340, 10, .009, 'de'],
    ['Zug', 47.1660, 8.5150, 12, .009, 'de'],
    ['Olten', 47.3500, 7.9030, 10, .008, 'de'],
    ['Baden', 47.4730, 8.3070, 10, .008, 'de'],
    ['Bellinzona', 46.1950, 9.0230, 10, .008, 'it'],
    ['Yverdon', 46.7785, 6.6410, 10, .008, 'fr'],
  ];

  function rng(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const pick = (r, arr) => arr[Math.floor(r() * arr.length)];
  const catKeys = Object.keys(CATEGORIES);

  function makeEvents(lat, lng, n, spread, lang, seed, idPrefix, city) {
    const r = rng(seed);
    const out = [];
    const lngScale = 1 / Math.cos(lat * Math.PI / 180);
    for (let i = 0; i < n; i++) {
      // Sum of uniforms ≈ normal: denser in the centre, thinning outwards
      const dx = (r() + r() + r() - 1.5) * spread * 1.6;
      const dy = (r() + r() + r() - 1.5) * spread * 1.6;
      const cat = pick(r, catKeys);
      out.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lng + dx * lngScale, lat + dy] },
        properties: {
          id: `${idPrefix}-${i}`,
          cat,
          color: CATEGORIES[cat].color,
          title: pick(r, TITLES[cat])(LANG[lang] || 'German'),
          when: `${pick(r, DAYS)} ${pick(r, TIMES)}`,
          venue: pick(r, VENUES),
          city,
          category: CATEGORIES[cat].label,
          about: ABOUT[cat],
          audience: AUDIENCE[cat],
          duration: pick(r, ['1 h', '1.5 h', '2 h', '2 h', '3 h']),
        },
      });
    }
    return out;
  }

  function generateEvents() {
    const features = [];
    CITIES.forEach(([name, lat, lng, n, spread, lang], ci) => {
      features.push(...makeEvents(lat, lng, Math.round(n * 1.5), spread, lang, 1000 + ci, name, name));
    });
    return { type: 'FeatureCollection', features };
  }

  // Extra events around any spot (used around the user's position so there is always something nearby)
  function eventsAround(lat, lng, n = 30) {
    const seed = Math.round(lat * 1000) * 7919 + Math.round(lng * 1000);
    const lang = lng < 7.1 ? 'fr' : lat < 46.4 && lng > 8.4 ? 'it' : 'de';
    return makeEvents(lat, lng, n, .012, lang, seed, `near-${seed}`, 'Near you');
  }

  window.EVENTS = { CATEGORIES, GLYPHS, generateEvents, eventsAround };
})();
