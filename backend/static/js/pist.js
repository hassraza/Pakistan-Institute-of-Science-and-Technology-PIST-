  // 1. Mobile Hamburger Drawer Functions
  window.openMobileNav = function() {
    const drawer = document.getElementById('mobile-nav-drawer') || document.querySelector('[data-site-nav]');
    const backdrop = document.getElementById('mobile-menu-backdrop');
    const toggle = document.getElementById('mobile-menu-toggle') || document.querySelector('[data-menu-toggle]');
    if (drawer) {
      drawer.classList.remove('translate-x-full');
      drawer.classList.add('translate-x-0', 'is-open');
    }
    if (backdrop) {
      backdrop.classList.remove('opacity-0', 'pointer-events-none');
      backdrop.classList.add('opacity-100', 'pointer-events-auto');
    }
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('overflow-hidden');
  };

  window.closeMobileNav = function() {
    const drawer = document.getElementById('mobile-nav-drawer') || document.querySelector('[data-site-nav]');
    const backdrop = document.getElementById('mobile-menu-backdrop');
    const toggle = document.getElementById('mobile-menu-toggle') || document.querySelector('[data-menu-toggle]');
    if (drawer) {
      drawer.classList.remove('translate-x-0', 'is-open');
      drawer.classList.add('translate-x-full');
    }
    if (backdrop) {
      backdrop.classList.remove('opacity-100', 'pointer-events-auto');
      backdrop.classList.add('opacity-0', 'pointer-events-none');
    }
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('overflow-hidden');
  };

  window.toggleMobileNav = function() {
    const drawer = document.getElementById('mobile-nav-drawer') || document.querySelector('[data-site-nav]');
    if (drawer && drawer.classList.contains('is-open')) {
      window.closeMobileNav();
    } else {
      window.openMobileNav();
    }
  };

  const mobileDrawer = document.getElementById('mobile-nav-drawer') || document.querySelector('[data-site-nav]');
  if (mobileDrawer) {
    mobileDrawer.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        if (window.closeMobileNav) window.closeMobileNav();
      });
    });
  }

  /* ==========================================================================
     2. Global Search Modal & Client-Side Search Engine
     ========================================================================== */
  const searchTrigger = document.getElementById('global-search-trigger');
  const mobileSearchTrigger = document.getElementById('mobile-search-trigger');
  const searchModal = document.getElementById('search-modal');
  const searchModalBox = document.getElementById('search-modal-box');
  const searchModalBackdrop = document.getElementById('search-modal-backdrop');
  const searchModalClose = document.getElementById('search-modal-close');
  const searchInput = document.getElementById('global-search-input');
  const searchClearBtn = document.getElementById('search-input-clear');
  const resultsContainer = document.getElementById('search-results-container');
  const categoryPills = document.querySelectorAll('[data-search-filter]');

  let activeCategory = 'all';
  let activeIndex = -1;
  let currentResults = [];
  let debounceTimeout = null;

  // Comprehensive University Knowledge Search Index
  const SEARCH_INDEX = [
    // --- Programs & Degrees ---
    {
      title: 'Bachelor of Science in Computer Science (BS CS)',
      category: 'Programs',
      level: 'Undergraduate',
      description: '4-year degree focusing on software development, algorithms, artificial intelligence, operating systems, and web technologies.',
      url: '/programs/bscs-isb/',
      keywords: 'cs bscs programming coding software backend frontend python java algorithms',
      icon: 'terminal'
    },
    {
      title: 'Master of Science in Computer Science (MS CS)',
      category: 'Programs',
      level: 'Graduate (Masters)',
      description: '2-year advanced degree in distributed computing, machine learning research, and cloud infrastructure.',
      url: '/programs/mscs-isb/',
      keywords: 'mscs graduate research distributed systems cloud ai masters',
      icon: 'terminal'
    },
    {
      title: 'Bachelor of Science in Artificial Intelligence (BS AI)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Machine learning, deep learning, computer vision, natural language processing, and robotics.',
      url: '/programs/bsai-isb/',
      keywords: 'ai bsai machine learning ml deep learning neural networks data neural bot',
      icon: 'psychology'
    },
    {
      title: 'Bachelor of Science in Data Science (BS DS)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Big data analytics, statistics, predictive modeling, data visualization, and data engineering.',
      url: '/programs/bsds-isb/',
      keywords: 'ds bsds data science analytics big data statistics visualization bi',
      icon: 'analytics'
    },
    {
      title: 'Bachelor of Science in Software Engineering (BS SE)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'DevOps, software architecture, quality assurance, system design, and agile methodologies.',
      url: '/programs/bsse-isb/',
      keywords: 'se bsse software engineering devops architecture testing qa design',
      icon: 'code'
    },
    {
      title: 'Master of Science in Software Engineering (MS SE)',
      category: 'Programs',
      level: 'Graduate (Masters)',
      description: 'Advanced software design patterns, enterprise system architecture, and project management.',
      url: '/programs/msse-isb/',
      keywords: 'msse masters software architect agile enterprise management',
      icon: 'code'
    },
    {
      title: 'Bachelor of Science in Cyber Security (BS CYS)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Ethical hacking, network defense, penetration testing, digital forensics, and cryptography.',
      url: '/programs/bscys-isb/',
      keywords: 'cys bscys cyber security hacking penetration testing network defense info sec',
      icon: 'security'
    },
    {
      title: 'Bachelor of Science in Information Technology (BS IT)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Enterprise IT systems, network infrastructure, database administration, and cloud services.',
      url: '/programs/bsit-isb/',
      keywords: 'it bsit information technology sysadmin network database cloud',
      icon: 'dns'
    },
    {
      title: 'Bachelor of Science in Electrical Engineering (BS EE)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Power systems, smart grid, telecommunications, embedded systems, and control engineering.',
      url: '/programs/bsee-isb/',
      keywords: 'ee bsee electrical engineering power electronics circuit hardware ecat',
      icon: 'bolt'
    },
    {
      title: 'Bachelor of Science in Mechanical Engineering (BS ME)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Thermodynamics, CAD/CAM, robotics, materials science, and manufacturing engineering.',
      url: '/programs/bsme-isb/',
      keywords: 'me bsme mechanical cad cam manufacturing robotics thermodynamics',
      icon: 'precision_manufacturing'
    },
    {
      title: 'Bachelor of Science in Civil Engineering (BS CE)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Structural engineering, transportation systems, geotechnical analysis, and construction management.',
      url: '/programs/bsce-isb/',
      keywords: 'ce bsce civil engineering construction structural survey building',
      icon: 'foundation'
    },
    {
      title: 'Doctor of Medicine (MBBS)',
      category: 'Programs',
      level: 'Undergraduate (5 Years)',
      description: '5-year professional clinical medicine and surgery training recognized by medical councils.',
      url: '/programs/mbbs-isb/',
      keywords: 'mbbs doctor medicine surgery mdcat hospital medical healthcare',
      icon: 'medical_services'
    },
    {
      title: 'Doctor of Pharmacy (PharmD)',
      category: 'Programs',
      level: 'Undergraduate (5 Years)',
      description: 'Clinical pharmacy practice, drug formulations, pharmacology, and pharmaceutical research.',
      url: '/programs/pharmd-isb/',
      keywords: 'pharmd pharmacy medicine pharmaceutical drugs pharmacology healthcare',
      icon: 'medication'
    },
    {
      title: 'Bachelor of Business Administration (BBA)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Corporate strategy, marketing management, human resources, and entrepreneurship.',
      url: '/programs/bba-isb/',
      keywords: 'bba business management administration marketing finance leadership corporate',
      icon: 'business_center'
    },
    {
      title: 'Master of Business Administration (MBA)',
      category: 'Programs',
      level: 'Graduate (Masters)',
      description: 'Strategic leadership, business analytics, financial decision-making, and executive consulting.',
      url: '/programs/mba-isb/',
      keywords: 'mba business executive management leadership finance consulting',
      icon: 'business_center'
    },
    {
      title: 'Bachelor of Science in Accounting and Finance (BS A&F)',
      category: 'Programs',
      level: 'Undergraduate',
      description: 'Auditing, corporate taxation, financial modeling, portfolio management, and banking.',
      url: '/programs/bsaf-isb/',
      keywords: 'acf accounting finance audit banking tax investment accounts',
      icon: 'account_balance'
    },
    {
      title: 'Bachelor of Laws (LLB)',
      category: 'Programs',
      level: 'Undergraduate (5 Years)',
      description: '5-year comprehensive legal education covering corporate law, constitutional law, and litigation.',
      url: '/programs/llb-isb/',
      keywords: 'llb law legal advocate attorney constitutional lat judiciary',
      icon: 'gavel'
    },

    // --- Admissions & Guidelines ---
    {
      title: 'Admissions 2026/2027 Overview & Step-by-Step Procedure',
      category: 'Admissions',
      description: 'Complete guide to admissions, step-by-step workflow from eligibility check to roll number slip issuance.',
      url: '/admissions/procedure/',
      keywords: 'admissions apply how to apply requirements process timeline fall spring steps',
      icon: 'school'
    },
    {
      title: 'Explore All Degree Programs & Deadlines',
      category: 'Admissions',
      description: 'Browse all available undergraduate and graduate programs across Islamabad, Lahore, and Karachi campuses.',
      url: '/programs/',
      keywords: 'browse programs search degrees all courses filter campuses departments',
      icon: 'list_alt'
    },
    {
      title: 'Eligibility Requirements & Merit Criteria',
      category: 'Admissions',
      description: 'Minimum intermediate/bachelor percentage criteria and test requirements (USAT, ECAT, MDCAT, LAT, PIST Test).',
      url: '/admissions/procedure/',
      keywords: 'eligibility criteria percentage marks minimum usat ecat mdcat lat test scores requirements',
      icon: 'fact_check'
    },
    {
      title: 'Track Application Status',
      category: 'Admissions',
      description: 'Real-time application verification and tracking using your Application ID or Program Registration ID.',
      url: '/admissions/track/',
      keywords: 'track status application id registration id check verify progress',
      icon: 'search_check'
    },

    // --- Departments & Faculties ---
    {
      title: 'Department of Computer Science',
      category: 'Departments',
      description: 'Programs in Computer Science, Artificial Intelligence, Data Science, Cyber Security, and IT.',
      url: '/programs/?department=CS',
      keywords: 'department cs computing technology artificial intelligence data science cyber security it',
      icon: 'apartment'
    },
    {
      title: 'Department of Software Engineering',
      category: 'Departments',
      description: 'Programs in software architecture, quality engineering, and product development.',
      url: '/programs/?department=SE',
      keywords: 'department software engineering se computing agile devops',
      icon: 'apartment'
    },
    {
      title: 'Department of Electrical Engineering',
      category: 'Departments',
      description: 'Power systems, smart grid, telecommunications, and electronics engineering.',
      url: '/programs/?department=EE',
      keywords: 'department electrical engineering ee power telecommunication electronics',
      icon: 'apartment'
    },
    {
      title: 'Department of Mechanical Engineering',
      category: 'Departments',
      description: 'Manufacturing systems, thermodynamics, automation, and aerospace engineering.',
      url: '/programs/?department=ME',
      keywords: 'department mechanical engineering me robotics manufacturing',
      icon: 'apartment'
    },
    {
      title: 'Department of Management Sciences',
      category: 'Departments',
      description: 'BBA, MBA, supply chain management, and executive entrepreneurship studies.',
      url: '/programs/?department=MGT',
      keywords: 'department management sciences business administration bba mba marketing',
      icon: 'apartment'
    },
    {
      title: 'Department of Health & Medical Sciences',
      category: 'Departments',
      description: 'Clinical medical education, MBBS, community health, and biomedical sciences.',
      url: '/programs/?department=HMS',
      keywords: 'department health medical sciences mbbs doctor medicine clinic',
      icon: 'apartment'
    },

    // --- Campuses & Locations ---
    {
      title: 'Islamabad Main Campus (ISB)',
      category: 'Campuses',
      description: 'Plot H-12, Sector H-12, Islamabad. Flagship university campus featuring advanced research facilities.',
      url: '/campuses/ISB/',
      keywords: 'islamabad isb main campus h12 federal territory capital central facilities',
      icon: 'location_on'
    },
    {
      title: 'Lahore Campus (LHR)',
      category: 'Campuses',
      description: 'Raiwind Road, Lahore, Punjab. State-of-the-art academic blocks, libraries, and student sports facilities.',
      url: '/campuses/LHR/',
      keywords: 'lahore lhr campus punjab raiwind road engineering computing business',
      icon: 'location_on'
    },
    {
      title: 'Karachi Campus (KHI)',
      category: 'Campuses',
      description: 'PECHS Block 6, Karachi, Sindh. Modern technology labs, incubation center, and multimedia facilities.',
      url: '/campuses/KHI/',
      keywords: 'karachi khi campus sindh pechs block tech hub coastal',
      icon: 'location_on'
    },
    {
      title: 'University Contact & Campus Directory',
      category: 'Campuses',
      description: 'Official phone directory, email contacts, admissions office locations, and helpline hours.',
      url: '/contact/',
      keywords: 'contact helpline email phone number location address directory support',
      icon: 'call'
    },

    // --- Portals & Resources ---
    {
      title: 'Student Portal Dashboard',
      category: 'Portals',
      description: 'Access student profile, academic records, document uploads, application progress, and test roll slips.',
      url: '/student/dashboard/',
      keywords: 'student portal dashboard login profile my application registered programs roll slip',
      icon: 'dashboard'
    },
    {
      title: 'Student Registration / Sign Up',
      category: 'Portals',
      description: 'Create a new applicant student account with your name, email, CNIC/B-Form, and password.',
      url: '/student/register/',
      keywords: 'create account sign up register new student applicant registration',
      icon: 'person_add'
    },
    {
      title: 'Student Portal Login',
      category: 'Portals',
      description: 'Log in to your PIST Student Portal account to view your application status and roll slips.',
      url: '/student/login/',
      keywords: 'login sign in access portal password credentials',
      icon: 'login'
    },
    {
      title: 'Academic Documents Upload',
      category: 'Portals',
      description: 'Upload CNIC, Matric/O-Level transcripts, Intermediate/A-Level certificates, and photographs.',
      url: '/student/documents/',
      keywords: 'documents upload matric inter fsc transcripts certificates degrees photos cnic',
      icon: 'upload_file'
    },
    {
      title: 'Research Publications & Labs',
      category: 'Portals',
      description: 'Discover scientific research papers, university labs, funding grants, and faculty innovations.',
      url: '/research/',
      keywords: 'research publications journals projects labs technology innovations',
      icon: 'science'
    },
    {
      title: 'Campus Life & Student Societies',
      category: 'Portals',
      description: 'Student clubs, sports events, robotics society, literary circle, and campus community life.',
      url: '/student-life/',
      keywords: 'campus life societies student clubs events sports cultural extra curricular',
      icon: 'celebration'
    },
    {
      title: 'About PIST University',
      category: 'Portals',
      description: 'Academic mission, vision, governance structure, and institutional profile.',
      url: '/about/',
      keywords: 'about university history mission vision chancellor rector pist info',
      icon: 'info'
    }
  ];

  function openSearchModal() {
    if (!searchModal) return;
    closeMobileMenu();
    searchModal.classList.remove('opacity-0', 'pointer-events-none');
    searchModal.classList.add('opacity-100', 'pointer-events-auto');
    if (searchModalBox) {
      searchModalBox.classList.remove('scale-95');
      searchModalBox.classList.add('scale-100');
    }
    if (searchModalBackdrop) {
      searchModalBackdrop.classList.remove('opacity-0', 'pointer-events-none');
      searchModalBackdrop.classList.add('opacity-100', 'pointer-events-auto');
    }
    if (searchTrigger) {
      searchTrigger.setAttribute('aria-expanded', 'true');
    }
    document.body.classList.add('overflow-hidden');
    setTimeout(() => {
      if (searchInput) {
        searchInput.focus();
        if (!searchInput.value.trim()) {
          renderInitialState();
        } else {
          performSearch(searchInput.value.trim());
        }
      }
    }, 50);
  }

  function closeSearchModal() {
    if (!searchModal) return;
    searchModal.classList.remove('opacity-100', 'pointer-events-auto');
    searchModal.classList.add('opacity-0', 'pointer-events-none');
    if (searchModalBox) {
      searchModalBox.classList.remove('scale-100');
      searchModalBox.classList.add('scale-95');
    }
    if (searchModalBackdrop) {
      searchModalBackdrop.classList.remove('opacity-100', 'pointer-events-auto');
      searchModalBackdrop.classList.add('opacity-0', 'pointer-events-none');
    }
    if (searchTrigger) {
      searchTrigger.setAttribute('aria-expanded', 'false');
      searchTrigger.focus();
    }
    document.body.classList.remove('overflow-hidden');
    activeIndex = -1;
  }

  function highlightMatches(text, query) {
    if (!query || !text) return text;
    const words = query.trim().split(/\s+/).filter(Boolean);
    if (!words.length) return text;
    const escaped = words.map(w => w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return text.replace(regex, '<mark class="bg-tertiary-fixed text-on-tertiary-fixed font-semibold px-0.5 rounded">$1</mark>');
  }

  function renderInitialState() {
    if (!resultsContainer) return;
    resultsContainer.innerHTML = `
      <div class="py-4">
        <div class="text-xs font-bold uppercase tracking-wider text-on-surface-variant/70 px-2 mb-3">Popular Searches</div>
        <div class="flex flex-wrap gap-2 px-2 mb-6">
          <button type="button" class="quick-suggestion-btn text-xs font-medium bg-surface-container-high hover:bg-primary hover:text-white px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5" data-search-term="Computer Science">
            <span class="material-symbols-outlined text-[14px]">search</span> Computer Science
          </button>
          <button type="button" class="quick-suggestion-btn text-xs font-medium bg-surface-container-high hover:bg-primary hover:text-white px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5" data-search-term="Artificial Intelligence">
            <span class="material-symbols-outlined text-[14px]">psychology</span> Artificial Intelligence
          </button>
          <button type="button" class="quick-suggestion-btn text-xs font-medium bg-surface-container-high hover:bg-primary hover:text-white px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5" data-search-term="Admissions">
            <span class="material-symbols-outlined text-[14px]">school</span> Admissions Guide
          </button>
          <button type="button" class="quick-suggestion-btn text-xs font-medium bg-surface-container-high hover:bg-primary hover:text-white px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5" data-search-term="Student Portal">
            <span class="material-symbols-outlined text-[14px]">dashboard</span> Student Portal
          </button>
          <button type="button" class="quick-suggestion-btn text-xs font-medium bg-surface-container-high hover:bg-primary hover:text-white px-3 py-1.5 rounded-md transition-colors flex items-center gap-1.5" data-search-term="Lahore Campus">
            <span class="material-symbols-outlined text-[14px]">location_on</span> Lahore Campus
          </button>
        </div>

        <div class="text-xs font-bold uppercase tracking-wider text-on-surface-variant/70 px-2 mb-2">Featured Degrees</div>
        <div class="flex flex-col gap-1.5">
          ${SEARCH_INDEX.slice(0, 4).map((item, idx) => `
            <a href="${item.url}" class="search-result-item flex items-center justify-between p-2.5 rounded-lg hover:bg-surface-container-high transition-colors group" data-result-index="${idx}">
              <div class="flex items-center gap-3">
                <span class="p-2 rounded-md bg-primary-fixed/20 text-primary group-hover:bg-primary group-hover:text-white transition-colors material-symbols-outlined text-[20px]">${item.icon}</span>
                <div>
                  <div class="text-sm font-semibold text-on-surface group-hover:text-primary transition-colors">${item.title}</div>
                  <div class="text-xs text-on-surface-variant line-clamp-1">${item.description}</div>
                </div>
              </div>
              <span class="material-symbols-outlined text-on-surface-variant/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all text-[18px]">chevron_right</span>
            </a>
          `).join('')}
        </div>
      </div>
    `;

    document.querySelectorAll('.quick-suggestion-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const term = btn.getAttribute('data-search-term');
        if (searchInput) {
          searchInput.value = term;
          if (searchClearBtn) searchClearBtn.classList.remove('hidden');
          performSearch(term);
        }
      });
    });
  }

  function performSearch(query) {
    if (!resultsContainer) return;
    const cleanQuery = query.toLowerCase().trim();

    if (!cleanQuery) {
      renderInitialState();
      currentResults = [];
      activeIndex = -1;
      return;
    }

    const queryTerms = cleanQuery.split(/\s+/).filter(Boolean);

    // Filter across dataset
    let filtered = SEARCH_INDEX.filter((item) => {
      // Category filter
      if (activeCategory !== 'all' && item.category !== activeCategory) {
        return false;
      }
      // Text match
      const searchableText = `${item.title} ${item.category} ${item.level || ''} ${item.description} ${item.keywords || ''}`.toLowerCase();
      return queryTerms.every(term => searchableText.includes(term));
    });

    currentResults = filtered;
    activeIndex = -1;

    if (filtered.length === 0) {
      resultsContainer.innerHTML = `
        <div class="py-10 text-center flex flex-col items-center justify-center">
          <span class="material-symbols-outlined text-outline-variant text-[48px] mb-3">search_off</span>
          <h3 class="text-base font-bold text-on-surface mb-1">No results found for "${query}"</h3>
          <p class="text-xs text-on-surface-variant max-w-sm mb-4">We couldn't find matching programs, admissions information, or campus portals. Try searching for broader terms.</p>
          <div class="flex flex-wrap items-center justify-center gap-2">
            <button type="button" class="empty-suggestion-btn text-xs font-semibold px-3 py-1 bg-surface-container-high hover:bg-primary hover:text-white rounded transition-colors" data-search-term="Admissions">Admissions</button>
            <button type="button" class="empty-suggestion-btn text-xs font-semibold px-3 py-1 bg-surface-container-high hover:bg-primary hover:text-white rounded transition-colors" data-search-term="Computer Science">Computer Science</button>
            <button type="button" class="empty-suggestion-btn text-xs font-semibold px-3 py-1 bg-surface-container-high hover:bg-primary hover:text-white rounded transition-colors" data-search-term="Campuses">Campuses</button>
            <button type="button" class="empty-suggestion-btn text-xs font-semibold px-3 py-1 bg-surface-container-high hover:bg-primary hover:text-white rounded transition-colors" data-search-term="Student Portal">Student Portal</button>
          </div>
        </div>
      `;
      document.querySelectorAll('.empty-suggestion-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
          const term = btn.getAttribute('data-search-term');
          if (searchInput) {
            searchInput.value = term;
            performSearch(term);
          }
        });
      });
      return;
    }

    // Group results by category
    const grouped = {};
    filtered.forEach((item) => {
      if (!grouped[item.category]) {
        grouped[item.category] = [];
      }
      grouped[item.category].push(item);
    });

    let html = '';
    let globalItemIdx = 0;

    for (const [catName, items] of Object.entries(grouped)) {
      html += `
        <div class="mb-4">
          <div class="text-[11px] font-bold uppercase tracking-wider text-primary px-2 mb-1.5 flex items-center justify-between">
            <span>${catName}</span>
            <span class="text-[10px] text-on-surface-variant font-normal">${items.length} ${items.length === 1 ? 'match' : 'matches'}</span>
          </div>
          <div class="flex flex-col gap-1">
            ${items.map((item) => {
              const idx = globalItemIdx++;
              return `
                <a href="${item.url}" class="search-result-item flex items-start gap-3 p-2.5 rounded-lg hover:bg-surface-container-high transition-colors group cursor-pointer focus:outline-none focus:ring-1 focus:ring-primary" data-result-index="${idx}" data-url="${item.url}">
                  <span class="p-2 rounded-md bg-surface-container-highest text-primary group-hover:bg-primary group-hover:text-white transition-colors material-symbols-outlined text-[18px] flex-shrink-0 mt-0.5">${item.icon}</span>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap">
                      <span class="text-sm font-semibold text-on-surface group-hover:text-primary transition-colors">${highlightMatches(item.title, query)}</span>
                      ${item.level ? `<span class="text-[10px] font-semibold uppercase px-2 py-0.5 rounded bg-surface-container-highest text-on-surface-variant">${item.level}</span>` : ''}
                    </div>
                    <p class="text-xs text-on-surface-variant/90 line-clamp-1 mt-0.5">${highlightMatches(item.description, query)}</p>
                  </div>
                  <span class="material-symbols-outlined text-on-surface-variant/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all text-[16px] flex-shrink-0 self-center">arrow_forward</span>
                </a>
              `;
            }).join('')}
          </div>
        </div>
      `;
    }

    resultsContainer.innerHTML = html;
  }

  window.renderInitialSearchState = renderInitialState;
  window.performSearch = performSearch;
  window.openSearchModal = openSearchModal;
  window.closeSearchModal = closeSearchModal;
  window.openMobileNav = openMobileMenu;
  window.closeMobileNav = closeMobileMenu;

  function updateActiveResult() {
    const items = resultsContainer ? resultsContainer.querySelectorAll('.search-result-item') : [];
    items.forEach((item, idx) => {
      if (idx === activeIndex) {
        item.classList.add('bg-surface-container-high', 'border-primary');
        item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        item.setAttribute('aria-selected', 'true');
      } else {
        item.classList.remove('bg-surface-container-high', 'border-primary');
        item.setAttribute('aria-selected', 'false');
      }
    });
  }



  // Input Typing & Instant Debounced Filtering
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const val = e.target.value;
      if (searchClearBtn) {
        searchClearBtn.classList.toggle('hidden', !val);
      }
      clearTimeout(debounceTimeout);
      debounceTimeout = setTimeout(() => {
        performSearch(val);
      }, 120);
    });

    // Keyboard Navigation Inside Search Input
    searchInput.addEventListener('keydown', (e) => {
      const items = resultsContainer ? resultsContainer.querySelectorAll('.search-result-item') : [];
      if (!items.length) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIndex = (activeIndex + 1) % items.length;
        updateActiveResult();
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIndex = (activeIndex - 1 + items.length) % items.length;
        updateActiveResult();
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (activeIndex >= 0 && items[activeIndex]) {
          items[activeIndex].click();
        } else if (items[0]) {
          items[0].click();
        }
      }
    });
  }

  if (searchClearBtn) {
    searchClearBtn.addEventListener('click', () => {
      if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
        searchClearBtn.classList.add('hidden');
        renderInitialState();
      }
    });
  }

  // Category Filter Tabs
  categoryPills.forEach((pill) => {
    pill.addEventListener('click', () => {
      categoryPills.forEach(p => {
        p.classList.remove('active', 'bg-primary', 'text-white');
        p.classList.add('bg-surface', 'text-on-surface-variant');
      });
      pill.classList.add('active', 'bg-primary', 'text-white');
      pill.classList.remove('bg-surface', 'text-on-surface-variant');
      activeCategory = pill.getAttribute('data-search-filter') || 'all';
      if (searchInput) {
        performSearch(searchInput.value);
      }
    });
  });

  // Global Keyboard Shortcuts (Cmd+K / Ctrl+K and Escape)
  document.addEventListener('keydown', (e) => {
    const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    const isShortcut = isMac ? (e.metaKey && e.key === 'k') : (e.ctrlKey && e.key === 'k');

    if (isShortcut) {
      e.preventDefault();
      const isOpen = searchModal && searchModal.classList.contains('opacity-100');
      if (isOpen) {
        closeSearchModal();
      } else {
        openSearchModal();
      }
    } else if (e.key === 'Escape') {
      if (searchModal && searchModal.classList.contains('opacity-100')) {
        e.preventDefault();
        closeSearchModal();
      }
    }
  });

  /* ==========================================================================
     4. Department Campus Selection Modal Handler
     ========================================================================== */
  const deptModal = document.getElementById('department-campus-modal');
  const deptModalBox = document.getElementById('dept-modal-box');
  const deptModalBackdrop = document.getElementById('department-campus-backdrop');
  const deptModalClose = document.getElementById('dept-modal-close');
  const deptModalCancel = document.getElementById('dept-modal-cancel');
  const deptModalTitle = document.getElementById('dept-modal-title');
  const deptModalSubtitle = document.getElementById('dept-modal-subtitle');
  const deptModalCampusesList = document.getElementById('dept-modal-campuses-list');

  function openDeptModal(deptName, campuses) {
    if (!deptModal || !deptModalCampusesList) return;
    
    if (deptModalTitle) {
      deptModalTitle.textContent = deptName;
    }
    if (deptModalSubtitle) {
      deptModalSubtitle.textContent = `Select a campus offering ${deptName}`;
    }

    deptModalCampusesList.innerHTML = campuses.map((campus) => {
      const isMuted = campus.programs_count === 0;
      return `
        <a href="${campus.url}" class="flex items-center justify-between p-3.5 rounded-lg border border-outline-variant hover:border-primary hover:bg-surface-container-low transition-all group min-h-[52px] ${isMuted ? 'opacity-60 bg-surface-container-low' : 'bg-surface hover:shadow-sm'}">
          <div class="flex items-center gap-3">
            <span class="p-2 rounded-md ${campus.is_main ? 'bg-secondary text-white' : 'bg-primary-fixed text-primary'} material-symbols-outlined text-[20px]">
              ${campus.is_main ? 'domain' : 'location_city'}
            </span>
            <div>
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-sm font-bold text-primary group-hover:text-secondary transition-colors">${campus.campus_name}</span>
                ${campus.is_main ? '<span class="text-[10px] bg-secondary/15 text-secondary font-bold px-1.5 py-0.5 rounded">Main Campus</span>' : ''}
              </div>
              <span class="text-xs text-on-surface-variant">${campus.campus_city}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-xs font-bold ${campus.programs_count > 0 ? 'bg-primary text-white' : 'bg-surface-container-high text-on-surface-variant'} px-2.5 py-1 rounded-full">
              ${campus.programs_count} ${campus.programs_count === 1 ? 'Program' : 'Programs'}
            </span>
            <span class="material-symbols-outlined text-on-surface-variant/40 group-hover:text-primary group-hover:translate-x-0.5 transition-all text-[18px]">arrow_forward</span>
          </div>
        </a>
      `;
    }).join('');

    deptModal.classList.remove('opacity-0', 'pointer-events-none');
    deptModal.classList.add('opacity-100', 'pointer-events-auto');
    if (deptModalBox) {
      deptModalBox.classList.remove('scale-95');
      deptModalBox.classList.add('scale-100');
    }
    if (deptModalBackdrop) {
      deptModalBackdrop.classList.remove('opacity-0', 'pointer-events-none');
      deptModalBackdrop.classList.add('opacity-100', 'pointer-events-auto');
    }
    document.body.classList.add('overflow-hidden');
  }

  function closeDeptModal() {
    if (!deptModal) return;
    deptModal.classList.remove('opacity-100', 'pointer-events-auto');
    deptModal.classList.add('opacity-0', 'pointer-events-none');
    if (deptModalBox) {
      deptModalBox.classList.remove('scale-100');
      deptModalBox.classList.add('scale-95');
    }
    if (deptModalBackdrop) {
      deptModalBackdrop.classList.remove('opacity-100', 'pointer-events-auto');
      deptModalBackdrop.classList.add('opacity-0', 'pointer-events-none');
    }
    document.body.classList.remove('overflow-hidden');
  }

  document.querySelectorAll('[data-campus-modal="true"]').forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const isSingle = item.getAttribute('data-is-single') === 'true';
      const singleUrl = item.getAttribute('data-single-url');
      const deptName = item.getAttribute('data-department-name') || 'Department';
      const campusesRaw = item.getAttribute('data-campuses');

      if (isSingle && singleUrl && singleUrl !== '#') {
        window.location.href = singleUrl;
        return;
      }

      try {
        const campuses = JSON.parse(campusesRaw || '[]');
        if (campuses.length === 1 && campuses[0].url) {
          window.location.href = campuses[0].url;
        } else {
          openDeptModal(deptName, campuses);
        }
      } catch (err) {
        console.error('Error parsing campuses data', err);
        if (singleUrl && singleUrl !== '#') {
          window.location.href = singleUrl;
        }
      }
    });
  });

  if (deptModalClose) deptModalClose.addEventListener('click', closeDeptModal);
  if (deptModalCancel) deptModalCancel.addEventListener('click', closeDeptModal);
  if (deptModalBackdrop) deptModalBackdrop.addEventListener('click', closeDeptModal);

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && deptModal && deptModal.classList.contains('opacity-100')) {
      closeDeptModal();
    }
  });

  /* ==========================================================================
     5. Utility Handlers
     ========================================================================== */
  document.querySelectorAll('[data-confirm]').forEach((element) => {
    element.addEventListener('submit', (event) => {
      const message = element.getAttribute('data-confirm');
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  document.querySelectorAll('[data-print-roll-slip]').forEach((button) => {
    button.addEventListener('click', () => window.print());
  });
});
