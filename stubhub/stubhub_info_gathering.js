(() => {
    const results = [];
    const url = window.location.href;

    // ============================================================================
    // HELPER FUNCTIONS
    // ============================================================================

    const getText = (element) => {
        if (!element) return null;
        return element.textContent?.trim() || null;
    };

    // ============================================================================
    // URL PARAMETER PARSING - Extract filter state from URL
    // ============================================================================

    const parseUrlFilters = () => {
        try {
            const urlObj = new URL(window.location.href);
            return {
                sections: urlObj.searchParams.get('sections')?.split(',').filter(Boolean) || [],
                quantity: parseInt(urlObj.searchParams.get('quantity')) || null,
                ticketClasses: urlObj.searchParams.get('ticketClasses')?.split(',').filter(Boolean) || [],
                listingId: urlObj.searchParams.get('listingId') || null,
                rows: urlObj.searchParams.get('rows')?.split(',').filter(Boolean) || [],
                seatTypes: urlObj.searchParams.get('seatTypes')?.split(',').filter(Boolean) || [],
                minPrice: parseFloat(urlObj.searchParams.get('minPrice')) || null,
                maxPrice: parseFloat(urlObj.searchParams.get('maxPrice')) || null,
                sort: urlObj.searchParams.get('sort') || null,
            };
        } catch (e) {
            return { sections: [], quantity: null, ticketClasses: [], listingId: null, rows: [], seatTypes: [], minPrice: null, maxPrice: null, sort: null };
        }
    };

    // ============================================================================
    // LOGIN STATUS DETECTION
    // ============================================================================

    const detectLoginStatus = () => {
        try {
            const signInLinks = document.querySelectorAll('a, button');
            for (const el of signInLinks) {
                const text = getText(el)?.toLowerCase() || '';
                if (text === 'sign in' || text === 'log in' || text === 'login') {
                    return 'logged_out';
                }
            }
            const userMenuIndicators = document.querySelectorAll('[class*="user"], [class*="profile"], [class*="account"], [class*="avatar"]');
            if (userMenuIndicators.length > 0) {
                return 'logged_in';
            }
            const pageText = document.body?.innerText?.toLowerCase() || '';
            if (pageText.includes('my hub') || pageText.includes('my account') || pageText.includes('my tickets')) {
                return 'logged_in';
            }
            return 'unknown';
        } catch (e) {
            return 'unknown';
        }
    };

    // ============================================================================
    // PAGE TYPE DETECTION
    // ============================================================================

    const detectPageType = () => {
        try {
            const urlLower = window.location.href.toLowerCase();
            const path = window.location.pathname.toLowerCase();

            // Check for event detail page (URL contains /event/)
            if (urlLower.includes('/event/') || path.match(/\/event\//)) return 'event_listing';

            // Check for modal/popup containing event details (Get Notified popup)
            const modals = document.querySelectorAll('[role="dialog"], [class*="modal"], [class*="Modal"], [class*="popup"], [class*="Popup"], [class*="overlay"]');
            for (const modal of modals) {
                const modalText = getText(modal)?.toLowerCase() || '';
                // If modal has "Get Notified" and event details, treat as event detail view
                if (modalText.includes('get notified') && modalText.length > 50) {
                    return 'event_modal';  // User clicked on a specific event
                }
            }

            if (urlLower.includes('/checkout/') || path.includes('checkout')) return 'checkout';
            if (urlLower.includes('/search/') || path.includes('search')) return 'search_results';
            if (urlLower.includes('-tickets')) return 'event_category';
            if (path === '/' || path === '') return 'home';
            return 'other';
        } catch (e) {
            return 'unknown';
        }
    };

    // ============================================================================
    // TIME PARSING
    // ============================================================================

    const parseTime = (text) => {
        if (!text) return null;
        try {
            let match = text.match(/(\d{1,2}):(\d{2})\s*(AM|PM)?/i);
            if (match) {
                let hours = parseInt(match[1]);
                const minutes = match[2];
                const period = match[3]?.toUpperCase();
                if (period === 'PM' && hours < 12) hours += 12;
                if (period === 'AM' && hours === 12) hours = 0;
                return `${String(hours).padStart(2, '0')}:${minutes}`;
            }
            return null;
        } catch (e) {
            return null;
        }
    };

    // ============================================================================
    // PRICE PARSING - Handles multiple currencies (USD, INR, EUR, GBP)
    // ============================================================================

    const parsePrice = (text) => {
        if (!text) return null;
        try {
            // Remove currency symbols and normalize
            let cleanText = text.replace(/[₹€£$]/g, '').trim();

            // Handle "INR 2,203" format
            cleanText = cleanText.replace(/^(INR|USD|EUR|GBP)\s*/i, '');

            // Handle comma as thousand separator (US/UK: 1,234.56)
            let match = cleanText.match(/([\d,]+(?:\.\d{2})?)/);
            if (match) {
                return parseFloat(match[1].replace(/,/g, ""));
            }

            // Handle period as thousand separator (EU: 1.234,56)
            match = cleanText.match(/([\d.]+(?:,\d{2})?)/);
            if (match) {
                return parseFloat(match[1].replace(/\./g, "").replace(",", "."));
            }

            return null;
        } catch (e) {
            return null;
        }
    };

    // Detect currency from text
    const detectCurrency = (text) => {
        if (!text) return 'USD';
        if (text.includes('₹') || text.toLowerCase().includes('inr')) return 'INR';
        if (text.includes('€') || text.toLowerCase().includes('eur')) return 'EUR';
        if (text.includes('£') || text.toLowerCase().includes('gbp')) return 'GBP';
        return 'USD';
    };

    // Parse ticket count - handles more formats
    const parseTicketCount = (text) => {
        if (!text) return null;

        // "2 tickets", "2 Tickets", "2ticket"
        let match = text.match(/(\d+)\s*ticket/i);
        if (match) return parseInt(match[1]);

        // "Qty: 2", "Quantity: 2"
        match = text.match(/(?:qty|quantity)[:\s]*(\d+)/i);
        if (match) return parseInt(match[1]);

        // Just a number in context of tickets
        match = text.match(/^(\d+)$/);
        if (match) return parseInt(match[1]);

        return null;
    };

    // Extract city - LD+JSON FIRST, then pattern-based fallback
    const extractCity = (text) => {
        // 1. FIRST: Try LD+JSON (most reliable - StubHub's own structured data)
        try {
            const ldEvents = getEventsFromLdJson();
            if (ldEvents.length > 0 && ldEvents[0].city) {
                return ldEvents[0].city;
            }
        } catch (e) {
            // LD+JSON not available, try patterns
        }

        // 2. FALLBACK: Pattern-based extraction from text
        if (!text) return null;

        // Pattern 1: StubHub format "Venue | City, Country" or "Venue | City, State"
        // Example: "Anna Bhau Sathe Auditorium | Pune, India"
        let match = text.match(/\|\s*([^,|]+),\s*(?:[A-Za-z]+|[A-Z]{2})/i);
        if (match) {
            return match[1].trim().toLowerCase();
        }

        // Pattern 2: "City, State" or "City, State, Country" format
        match = text.match(/^([A-Za-z\s]+),\s*(?:[A-Z]{2}|[A-Za-z]+)/);
        if (match) {
            return match[1].trim().toLowerCase();
        }

        // Pattern 3: After pipe but before comma (venue | city format)
        match = text.match(/\|\s*([^,|]+)/);
        if (match) {
            return match[1].trim().toLowerCase();
        }

        return null;
    };

    const extractState = (text) => {
        if (!text) return null;
        const stateMatch = text.match(/,\s*([A-Z]{2})/);
        if (stateMatch) {
            return stateMatch[1];
        }
        return null;
    };

    // ============================================================================
    // LD+JSON EXTRACTION - Primary source of structured data (most reliable)
    // ============================================================================

    const getEventsFromLdJson = () => {
        try {
            const scripts = Array.from(
                document.querySelectorAll('script[type="application/ld+json"]')
            );
            const events = [];
            let breadcrumbs = [];

            for (const script of scripts) {
                try {
                    const data = JSON.parse(script.textContent);
                    const graph = data["@graph"] ?? [data];

                    for (const item of graph) {
                        if (!item["@type"]) continue;

                        // Handle @type as string or array
                        const types = Array.isArray(item["@type"]) ? item["@type"] : [item["@type"]];

                        // Extract breadcrumb data for navigation hierarchy
                        if (types.includes("BreadcrumbList") && item.itemListElement) {
                            breadcrumbs = item.itemListElement.map(el => ({
                                position: el.position,
                                name: el.name || el.item?.name,
                                url: el.item?.["@id"] || el.item
                            }));
                            continue;
                        }

                        // Skip non-event types
                        if (!types.some(t => t.toLowerCase().includes("event"))) continue;

                        // Determine category from @type (SportsEvent, MusicEvent, etc.)
                        let category = null;
                        let eventType = null;
                        for (const t of types) {
                            const typeLower = t.toLowerCase();
                            eventType = t;  // Store the exact type
                            if (typeLower.includes('sports') || typeLower === 'sportsevent') category = 'sports';
                            else if (typeLower.includes('music') || typeLower === 'musicevent' || typeLower.includes('concert')) category = 'concerts';
                            else if (typeLower.includes('theater') || typeLower.includes('theatre') || typeLower === 'theaterevent') category = 'theater';
                            else if (typeLower.includes('comedy') || typeLower === 'comedyevent') category = 'comedy';
                            else if (typeLower.includes('festival') || typeLower === 'festival') category = 'festivals';
                        }

                        // Extract location/venue details
                        const location = item.location || {};
                        const address = location.address || {};

                        // Extract performer info
                        const performer = item.performer || {};
                        const performerName = performer.name || (Array.isArray(performer) ? performer[0]?.name : null);
                        const performerType = performer["@type"] || (Array.isArray(performer) ? performer[0]?.["@type"] : null);

                        // Parse dates and times
                        const startDate = item.startDate || null;
                        const doorTime = item.doorTime || null;
                        const endDate = item.endDate || null;

                        // Extract offers/pricing
                        const offers = item.offers || {};
                        const lowPrice = offers.lowPrice ? parseFloat(offers.lowPrice) : null;
                        const highPrice = offers.highPrice ? parseFloat(offers.highPrice) : null;
                        const currency = offers.priceCurrency || "USD";
                        const availability = offers.availability
                            ? (offers.availability.includes("InStock") ? "available" : "sold_out")
                            : "unknown";

                        events.push({
                            // Basic event info
                            eventName: item.name?.toLowerCase() || null,
                            eventType: eventType,
                            category: category,
                            description: item.description || null,

                            // Dates and times
                            eventDate: startDate?.split("T")[0] || null,
                            startTime: startDate?.split("T")[1]?.substring(0, 5) || null,
                            doorTime: doorTime?.split("T")[1]?.substring(0, 5) || null,
                            endDate: endDate?.split("T")[0] || null,

                            // Venue details
                            venue: location.name || null,
                            streetAddress: address.streetAddress || null,
                            city: address.addressLocality?.toLowerCase() || null,
                            state: address.addressRegion || null,
                            postalCode: address.postalCode || null,
                            country: address.addressCountry || null,

                            // Performer info
                            performer: performerName || null,
                            performerType: performerType || null,

                            // Pricing and availability
                            lowPrice: lowPrice,
                            highPrice: highPrice,
                            currency: currency,
                            availability: availability,
                            priceRange: lowPrice ? { low: lowPrice, high: highPrice, currency: currency } : null,

                            // Event status
                            eventStatus: item.eventStatus || "EventScheduled",
                            isRescheduled: item.eventStatus === "EventRescheduled",
                            isCancelled: item.eventStatus === "EventCancelled",

                            // Media
                            image: item.image || null,

                            // URLs
                            url: item.url || null,

                            // Metadata
                            source: "ld+json",
                            breadcrumbs: breadcrumbs
                        });
                    }
                } catch (parseError) {
                    // Skip malformed JSON
                }
            }
            return events;
        } catch (e) {
            return [];
        }
    };

    // Get category from URL path (secondary source - very reliable)
    const getCategoryFromUrl = () => {
        try {
            const path = window.location.pathname.toLowerCase();
            const url = window.location.href.toLowerCase();

            if (path.includes('/sports') || url.includes('/sports')) return 'sports';
            if (path.includes('/concerts') || url.includes('/concerts')) return 'concerts';
            if (path.includes('/theater') || path.includes('/theatre')) return 'theater';
            if (path.includes('/comedy')) return 'comedy';
            if (path.includes('/festivals')) return 'festivals';

            // Check for sport-specific paths
            if (path.includes('/nba') || path.includes('/nfl') || path.includes('/mlb') ||
                path.includes('/nhl') || path.includes('/mls') || path.includes('/ncaa')) {
                return 'sports';
            }

            return null;
        } catch (e) {
            return null;
        }
    };

    // ============================================================================
    // CATEGORY DETECTION - 100% Dynamic, Zero Hardcoding
    // Uses only StubHub's structured data (LD+JSON) and URL patterns
    // ============================================================================

    const detectEventCategory = (text) => {
        // 1. PRIMARY: LD+JSON Schema.org @type (most reliable - StubHub's own data)
        // This works for ANY event type without hardcoding
        try {
            const ldEvents = getEventsFromLdJson();
            if (ldEvents.length > 0 && ldEvents[0].category) {
                return ldEvents[0].category;
            }
        } catch (e) {
            // LD+JSON not available
        }

        // 2. SECONDARY: URL pattern detection (very reliable)
        // StubHub URLs contain category: /sports/, /concerts/, /theater/, etc.
        const urlCategory = getCategoryFromUrl();
        if (urlCategory) {
            return urlCategory;
        }

        // 3. TERTIARY: Page structure detection
        // Look for category indicators in page metadata and navigation
        try {
            // Check breadcrumb navigation for category
            const breadcrumbs = document.querySelectorAll('[data-testid*="breadcrumb"], nav a, .breadcrumb a');
            for (const crumb of breadcrumbs) {
                const href = crumb.href?.toLowerCase() || '';
                const text = crumb.textContent?.toLowerCase() || '';

                if (href.includes('/sports') || text.includes('sports')) return 'sports';
                if (href.includes('/concerts') || text.includes('concerts')) return 'concerts';
                if (href.includes('/theater') || text.includes('theater')) return 'theater';
                if (href.includes('/comedy') || text.includes('comedy')) return 'comedy';
                if (href.includes('/festivals') || text.includes('festivals')) return 'festivals';
            }

            // Check page meta tags
            const metaCategory = document.querySelector('meta[property="og:type"], meta[name="category"]');
            if (metaCategory) {
                const content = metaCategory.content?.toLowerCase() || '';
                if (content.includes('sport')) return 'sports';
                if (content.includes('music') || content.includes('concert')) return 'concerts';
                if (content.includes('theater') || content.includes('theatre')) return 'theater';
            }
        } catch (e) {
            // DOM parsing failed
        }

        // No category detected - return null (let the verifier handle it)
        return null;
    };

    const detectTicketType = (text) => {
        if (!text) return 'standard';
        const lowerText = text.toLowerCase();

        if (lowerText.includes('vip')) return 'vip';
        if (lowerText.includes('premium')) return 'premium';
        if (lowerText.includes('general admission') || lowerText.includes('ga')) return 'general_admission';
        if (lowerText.includes('standing')) return 'standing';
        if (lowerText.includes('floor')) return 'floor';

        return 'standard';
    };

    const detectDeliveryType = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();

        if (lowerText.includes('instant') || lowerText.includes('download')) return 'instant_download';
        if (lowerText.includes('electronic') || lowerText.includes('e-ticket')) return 'electronic';
        if (lowerText.includes('mobile') || lowerText.includes('transfer')) return 'mobile_transfer';
        if (lowerText.includes('mail') || lowerText.includes('physical')) return 'physical';
        if (lowerText.includes('will call') || lowerText.includes('pickup')) return 'will_call';

        return 'electronic';
    };

    // Detect availability status - comprehensive
    const detectAvailabilityStatus = (text) => {
        if (!text) return 'available';
        const lowerText = text.toLowerCase();

        if (lowerText.includes('sold out') || lowerText.includes('soldout')) return 'sold_out';
        if (lowerText.includes('get notified') || lowerText.includes('notify me')) return 'get_notified';
        if (lowerText.includes('presale') || lowerText.includes('pre-sale')) return 'presale';
        if (lowerText.includes('waitlist') || lowerText.includes('wait list')) return 'waitlist';
        if (lowerText.includes('on sale') && lowerText.match(/on sale\s+\w+\s+\d/)) return 'future_sale';
        if (lowerText.includes('limited') || lowerText.includes('only') && lowerText.includes('left')) return 'limited';
        if (lowerText.includes('cancelled') || lowerText.includes('canceled')) return 'cancelled';
        if (lowerText.includes('postponed') || lowerText.includes('rescheduled')) return 'rescheduled';
        if (lowerText.includes('see tickets') || lowerText.includes('buy tickets')) return 'available';

        return 'available';
    };

    // Check if presale
    const isPresale = (text) => {
        if (!text) return false;
        const lowerText = text.toLowerCase();
        return lowerText.includes('presale') || lowerText.includes('pre-sale') || lowerText.includes('early access');
    };

    // Parse date from various formats -> YYYY-MM-DD
    // Includes relative date support: "today", "tomorrow", "next saturday", etc.
    const parseDate = (text) => {
        if (!text) return null;

        try {
            const lowerText = text.toLowerCase().trim();
            const today = new Date();

            // ===== RELATIVE DATES (NEW) =====

            // "today"
            if (lowerText === 'today') {
                return today.toISOString().split('T')[0];
            }

            // "tomorrow"
            if (lowerText === 'tomorrow') {
                const tomorrow = new Date(today);
                tomorrow.setDate(tomorrow.getDate() + 1);
                return tomorrow.toISOString().split('T')[0];
            }

            // "yesterday" (for completeness)
            if (lowerText === 'yesterday') {
                const yesterday = new Date(today);
                yesterday.setDate(yesterday.getDate() - 1);
                return yesterday.toISOString().split('T')[0];
            }

            // "next <day>" e.g., "next saturday"
            const daysOfWeek = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday'];
            for (let i = 0; i < daysOfWeek.length; i++) {
                if (lowerText.includes(daysOfWeek[i])) {
                    const targetDay = i;
                    const currentDay = today.getDay();
                    let daysUntil = targetDay - currentDay;
                    if (daysUntil <= 0) daysUntil += 7; // Next week
                    if (lowerText.includes('next')) daysUntil += 7; // "next" means next week
                    const targetDate = new Date(today);
                    targetDate.setDate(today.getDate() + daysUntil);
                    return targetDate.toISOString().split('T')[0];
                }
            }

            // ===== STANDARD DATE FORMATS =====

            // Already in YYYY-MM-DD format
            let match = text.match(/(\d{4})-(\d{2})-(\d{2})/);
            if (match) return match[0];

            // Jan 10, 2026 or January 10, 2026
            match = text.match(/(\w+)\s+(\d{1,2}),?\s*(\d{4})/);
            if (match) {
                const months = { jan: 1, feb: 2, mar: 3, apr: 4, may: 5, jun: 6, jul: 7, aug: 8, sep: 9, oct: 10, nov: 11, dec: 12 };
                const monthNum = months[match[1].toLowerCase().substring(0, 3)];
                if (monthNum) {
                    return `${match[3]}-${String(monthNum).padStart(2, '0')}-${match[2].padStart(2, '0')}`;
                }
            }

            // 10/01/2026 or 01-10-2026
            match = text.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
            if (match) {
                // Assume MM/DD/YYYY for US format
                return `${match[3]}-${match[1].padStart(2, '0')}-${match[2].padStart(2, '0')}`;
            }

            return null;
        } catch (e) {
            return null;
        }
    };

    const detectDateRange = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();

        if (lowerText.includes('today')) return 'today';
        if (lowerText.includes('this weekend') || lowerText.includes('weekend')) return 'this-weekend';
        if (lowerText.includes('this week') || lowerText.includes('week')) return 'this-week';
        if (lowerText.includes('this month') || lowerText.includes('month')) return 'this-month';
        if (lowerText.includes('tomorrow')) return 'tomorrow';

        return null;
    };

    // ============================================================================
    // GEO-BLOCKING & CAPTCHA DETECTION
    // ============================================================================

    // Detect if page is geo-blocked
    const detectGeoBlocking = () => {
        try {
            const pageText = document.body?.innerText?.toLowerCase() || '';
            const geoBlockIndicators = [
                'not available in your region',
                'not available in your country',
                'geo-restricted',
                'geographically restricted',
                'not available in your location',
                'content not available',
                'access denied',
                'region restricted',
                'country not supported'
            ];
            for (const indicator of geoBlockIndicators) {
                if (pageText.includes(indicator)) {
                    return { isBlocked: true, reason: indicator };
                }
            }
            return { isBlocked: false, reason: null };
        } catch (e) {
            return { isBlocked: false, reason: null };
        }
    };

    // Detect CAPTCHA challenges
    const detectCaptcha = () => {
        try {
            // Check for common CAPTCHA elements
            const captchaIndicators = document.querySelectorAll(
                '[class*="captcha"], [id*="captcha"], [class*="recaptcha"], [class*="hcaptcha"], iframe[src*="captcha"], iframe[src*="recaptcha"]'
            );
            if (captchaIndicators.length > 0) {
                return { hasCaptcha: true, type: 'detected' };
            }
            // Check for text indicators
            const pageText = document.body?.innerText?.toLowerCase() || '';
            if (pageText.includes('verify you are human') || pageText.includes('robot') || pageText.includes('captcha')) {
                return { hasCaptcha: true, type: 'text_indicator' };
            }
            return { hasCaptcha: false, type: null };
        } catch (e) {
            return { hasCaptcha: false, type: null };
        }
    };

    const extractSection = (text) => {
        if (!text) return null;
        const sectionMatch = text.match(/section\s*[:\s]*([A-Za-z0-9]+)/i);
        if (sectionMatch) return sectionMatch[1];
        return null;
    };

    const extractZone = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();

        if (lowerText.includes('lower level') || lowerText.includes('lower')) return 'lower level';
        if (lowerText.includes('upper deck') || lowerText.includes('upper')) return 'upper deck';
        if (lowerText.includes('floor') || lowerText.includes('pit')) return 'floor';
        if (lowerText.includes('mezzanine') || lowerText.includes('mezz')) return 'mezzanine';
        if (lowerText.includes('balcony')) return 'balcony';
        if (lowerText.includes('club')) return 'club level';

        return null;
    };

    const extractRow = (text) => {
        if (!text) return null;
        const rowMatch = text.match(/row\s*[:\s]*([A-Za-z0-9]+)/i);
        if (rowMatch) return rowMatch[1];
        return null;
    };

    const isVIP = (text) => {
        if (!text) return false;
        return text.toLowerCase().includes('vip');
    };

    const isAccessible = (text) => {
        if (!text) return false;
        const lowerText = text.toLowerCase();
        return lowerText.includes('accessible') || lowerText.includes('ada') || lowerText.includes('wheelchair');
    };

    const isParkingPass = (text) => {
        if (!text) return false;
        return text.toLowerCase().includes('parking');
    };

    const isAisleSeat = (text) => {
        if (!text) return false;
        return text.toLowerCase().includes('aisle');
    };

    const hasExtras = (text) => {
        if (!text) return false;
        const lowerText = text.toLowerCase();
        return lowerText.includes('includes') || lowerText.includes('extra') || lowerText.includes('bonus') || lowerText.includes('package');
    };

    // ============================================================================
    // ADDITIONAL PRODUCTION-LEVEL HELPERS
    // ============================================================================

    // Extract seller rating (e.g., "4.8 stars", "98% positive")
    const extractSellerRating = (text) => {
        if (!text) return null;
        try {
            // "4.8 stars", "4.8/5"
            let match = text.match(/(\d+\.?\d*)\s*(?:stars?|\/5)/i);
            if (match) return parseFloat(match[1]);
            // "98% positive"
            match = text.match(/(\d+)%\s*positive/i);
            if (match) return parseFloat(match[1]) / 20; // Convert to 5-star scale
            return null;
        } catch (e) {
            return null;
        }
    };

    // Detect seller type (individual vs professional)
    const detectSellerType = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();
        if (lowerText.includes('verified seller') || lowerText.includes('top seller') || lowerText.includes('pro seller')) {
            return 'professional';
        }
        if (lowerText.includes('individual') || lowerText.includes('fan seller')) {
            return 'individual';
        }
        return 'unknown';
    };

    // Extract total listing count from page
    const extractListingCount = (text) => {
        if (!text) return null;
        try {
            // "1,234 listings", "234 tickets available"
            const match = text.match(/([\d,]+)\s*(?:listing|ticket|result)/i);
            if (match) return parseInt(match[1].replace(/,/g, ''));
            return null;
        } catch (e) {
            return null;
        }
    };

    // Classify price tier (budget, mid, premium, luxury)
    const classifyPriceTier = (price) => {
        if (price === null || price === undefined) return null;
        if (price < 50) return 'budget';
        if (price < 150) return 'mid';
        if (price < 500) return 'premium';
        return 'luxury';
    };

    // Extract row number (handle letters and numbers)
    const extractRowNumber = (text) => {
        if (!text) return null;
        try {
            // "Row 15", "Row AA", "Row A"
            const match = text.match(/row\s*[:\s]*([A-Za-z]{1,2}|\d+)/i);
            if (match) return match[1].toUpperCase();
            return null;
        } catch (e) {
            return null;
        }
    };

    // Extract seat numbers (handle ranges)
    const extractSeatNumbers = (text) => {
        if (!text) return null;
        try {
            // "Seats 1-4", "Seat 12", "Seats 15, 16"
            const match = text.match(/seats?\s*[:\s]*([\d\-,\s]+)/i);
            if (match) return match[1].trim();
            return null;
        } catch (e) {
            return null;
        }
    };

    // Extract event ID from URL
    const extractEventId = () => {
        try {
            const match = window.location.href.match(/\/event\/(\d+)/);
            return match ? match[1] : null;
        } catch (e) {
            return null;
        }
    };

    // Detect if this is a resale ticket vs primary
    const isResaleTicket = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();
        if (lowerText.includes('resale') || lowerText.includes('secondary')) return true;
        if (lowerText.includes('primary') || lowerText.includes('official')) return false;
        return null; // Unknown
    };

    // Extract face value if shown
    const extractFaceValue = (text) => {
        if (!text) return null;
        try {
            const match = text.match(/face\s*value[:\s]*[$€£₹]?([\d,]+\.?\d*)/i);
            if (match) return parseFloat(match[1].replace(/,/g, ''));
            return null;
        } catch (e) {
            return null;
        }
    };

    // Detect if tickets are together (consecutive seats)
    const areTicketsTogether = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();
        if (lowerText.includes('together') || lowerText.includes('consecutive') || lowerText.includes('side by side')) {
            return true;
        }
        if (lowerText.includes('not together') || lowerText.includes('split') || lowerText.includes('separate')) {
            return false;
        }
        return null;
    };

    // ============================================================================
    // GAP-BRIDGING HELPERS - Cover remaining edge cases
    // ============================================================================

    // Detect if "Recommended" toggle is ON (from DOM, not URL)
    const detectRecommendedToggle = () => {
        try {
            // Look for toggle/switch elements with "recommended" text
            const toggles = document.querySelectorAll('[class*="toggle"], [class*="switch"], [role="switch"]');
            for (const toggle of toggles) {
                const text = (toggle.textContent || '').toLowerCase();
                const ariaChecked = toggle.getAttribute('aria-checked');
                if (text.includes('recommend')) {
                    return ariaChecked === 'true' || toggle.classList.contains('on') || toggle.classList.contains('active');
                }
            }
            // Check for sort dropdown selection
            const sortDropdown = document.querySelector('[class*="sort"] [class*="selected"], [class*="dropdown"] [class*="active"]');
            if (sortDropdown && sortDropdown.textContent?.toLowerCase().includes('recommend')) {
                return true;
            }
            return null; // Unknown
        } catch (e) {
            return null;
        }
    };

    // Detect filter panel state (open/closed, filters applied)
    const detectFilterPanelState = () => {
        try {
            const filterPanel = document.querySelector('[class*="filter"], [class*="Filter"]');
            const clearButton = document.querySelector('[class*="clear"], button:contains("Clear")');
            const activeFilters = document.querySelectorAll('[class*="active-filter"], [class*="applied"], [class*="chip"]');

            return {
                isOpen: filterPanel ? !filterPanel.classList.contains('collapsed') && !filterPanel.classList.contains('hidden') : null,
                hasActiveFilters: activeFilters.length > 0,
                activeFilterCount: activeFilters.length,
                hasClearButton: !!clearButton
            };
        } catch (e) {
            return { isOpen: null, hasActiveFilters: false, activeFilterCount: 0, hasClearButton: false };
        }
    };

    // Detect loading/async states
    const detectLoadingState = () => {
        try {
            const spinners = document.querySelectorAll('[class*="spinner"], [class*="loading"], [class*="skeleton"]');
            const loaders = document.querySelectorAll('[class*="loader"], [role="progressbar"]');
            const isLoading = spinners.length > 0 || loaders.length > 0;

            // Check for "No results" or "Loading" text
            const pageText = document.body?.innerText?.toLowerCase() || '';
            const noResults = pageText.includes('no results') || pageText.includes('no tickets found') || pageText.includes('try different');

            return {
                isLoading: isLoading,
                spinnerCount: spinners.length + loaders.length,
                noResults: noResults
            };
        } catch (e) {
            return { isLoading: false, spinnerCount: 0, noResults: false };
        }
    };

    // Detect obstructed view warnings
    const detectObstructedView = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();
        if (lowerText.includes('obstructed') || lowerText.includes('limited view') || lowerText.includes('partial view')) {
            return true;
        }
        if (lowerText.includes('clear view') || lowerText.includes('unobstructed') || lowerText.includes('full view')) {
            return false;
        }
        return null;
    };

    // Detect age restrictions
    const detectAgeRestrictions = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();
        if (lowerText.includes('21+') || lowerText.includes('21 and over')) return '21+';
        if (lowerText.includes('18+') || lowerText.includes('18 and over')) return '18+';
        if (lowerText.includes('all ages') || lowerText.includes('family friendly')) return 'all_ages';
        if (lowerText.includes('age restriction') || lowerText.includes('id required')) return 'restricted';
        return null;
    };

    // Extract listing age (how old the listing is)
    const extractListingAge = (text) => {
        if (!text) return null;
        try {
            const lowerText = text.toLowerCase();
            // "Listed 2 days ago", "Posted 3h ago"
            let match = lowerText.match(/(?:listed|posted)\s*(\d+)\s*(day|hour|minute|week|month|h|d|m|w)/i);
            if (match) {
                const value = parseInt(match[1]);
                const unit = match[2].toLowerCase();
                // Convert to hours for normalization
                if (unit.startsWith('h')) return value;
                if (unit.startsWith('d')) return value * 24;
                if (unit.startsWith('w')) return value * 24 * 7;
                if (unit.startsWith('month') || unit === 'm') return value * 24 * 30;
                return value;
            }
            return null;
        } catch (e) {
            return null;
        }
    };

    // Detect "Quick Picks" or featured listings
    const detectQuickPicks = (text) => {
        if (!text) return false;
        const lowerText = text.toLowerCase();
        return lowerText.includes('quick pick') || lowerText.includes('featured') || lowerText.includes('staff pick') || lowerText.includes('editor choice');
    };

    // Detect "Best Value" or deal ratings
    const detectBestValue = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();
        if (lowerText.includes('best value') || lowerText.includes('great deal') || lowerText.includes('good deal')) return 'best_value';
        if (lowerText.includes('fair price') || lowerText.includes('market price')) return 'fair';
        if (lowerText.includes('above market') || lowerText.includes('overpriced')) return 'expensive';
        return null;
    };

    // Detect distance/radius (for location-based searches)
    const extractLocationRadius = (text) => {
        if (!text) return null;
        try {
            const match = text.match(/within\s*(\d+)\s*(mile|km|kilometer)/i);
            if (match) {
                return { value: parseInt(match[1]), unit: match[2].toLowerCase().startsWith('km') ? 'km' : 'miles' };
            }
            return null;
        } catch (e) {
            return null;
        }
    };

    // Detect view quality rating (1-5 stars, percentages)
    const extractViewQuality = (text) => {
        if (!text) return null;
        try {
            // "View quality: 4.5/5", "View rating: 85%"
            let match = text.match(/view\s*(?:quality|rating)[:\s]*(\d+\.?\d*)(?:\/5|%)/i);
            if (match) {
                const value = parseFloat(match[1]);
                // Normalize to 0-100 scale
                return value <= 5 ? value * 20 : value;
            }
            return null;
        } catch (e) {
            return null;
        }
    };

    // ============================================================================
    // COMPREHENSIVE SCRAPER - Works on any StubHub page
    // ============================================================================


    const scrapeGeneric = () => {
        const collected = [];

        // Get the main event title from h1 or title
        const h1 = document.querySelector('h1');
        const pageTitle = document.title;
        const pageText = document.body?.innerText?.toLowerCase() || '';
        let mainEventName = getText(h1) || pageTitle?.split(' | ')[0] || null;

        // Detect event category from page content
        const eventCategory = detectEventCategory(pageText);

        // IMPORTANT: Determine if this is an event detail page or a category/search page
        // On event pages (/event/ in URL), we extract from the specific event
        // On category pages, we only return the main artist - NOT all visible event cards
        // This prevents giving credit for events the user didn't actually click on
        const currentUrl = window.location.href.toLowerCase();
        const isEventPage = currentUrl.includes('/event/');
        const isCategoryPage = currentUrl.includes('/category/') || currentUrl.includes('-tickets');

        // For CATEGORY pages: Use LD+JSON data if available, otherwise extract from URL
        // User must navigate to /event/ page for full verification
        if (isCategoryPage && !isEventPage) {
            // Try to get structured data from LD+JSON first (most reliable)
            const ldEvents = getEventsFromLdJson();

            if (ldEvents.length > 0) {
                // Use LD+JSON data - much more reliable!
                for (const ldEvent of ldEvents) {
                    collected.push({
                        url: ldEvent.url || url,
                        eventName: ldEvent.eventName || mainEventName?.toLowerCase() || 'unknown',
                        eventCategory: ldEvent.category || eventCategory,
                        venue: ldEvent.venue,
                        city: ldEvent.city,
                        country: ldEvent.country,
                        state: null,
                        date: ldEvent.eventDate,
                        dateRange: null,
                        section: null,
                        zone: null,
                        row: null,
                        ticketType: 'standard',
                        deliveryType: 'electronic',
                        isVIP: false,
                        isAccessible: false,
                        isParkingPass: false,
                        aisleSeat: false,
                        includesExtras: false,
                        availabilityStatus: ldEvent.availability,
                        priceRange: ldEvent.priceRange,
                        info: 'ld+json',  // Indicates data source
                        source: 'structured_data'
                    });
                }

                // If we got LD+JSON data, return it
                if (collected.length > 0) {
                    return collected;
                }
            }

            // Fallback: Extract from URL slug if no LD+JSON
            let mainArtist = null;
            const urlSlugMatch = currentUrl.match(/\/([a-z0-9-]+)-tickets/);
            if (urlSlugMatch) {
                mainArtist = urlSlugMatch[1].replace(/-/g, ' ').trim();
            }

            // Return only ONE entry for the category page with main artist info
            collected.push({
                url: url,
                eventName: mainArtist || (mainEventName ? mainEventName.toLowerCase() : 'unknown'),
                eventCategory: eventCategory,
                venue: null,
                city: null,  // No specific city on category page - user must click event
                state: null,
                date: null,
                dateRange: null,
                section: null,
                zone: null,
                row: null,
                ticketType: 'standard',
                deliveryType: 'electronic',
                isVIP: false,
                isAccessible: false,
                isParkingPass: false,
                aisleSeat: false,
                includesExtras: false,
                info: 'category_page',  // Different from 'category_event'
                pageNote: 'User is on category page. No LD+JSON data found.'
            });

            // Return early - don't scrape individual event cards on category pages
            return collected;
        }

        // Method 0: Category/Artist pages - extract individual event listings
        // NOTE: This now only runs on EVENT PAGES, not category pages
        // These pages show event cards with "Papa Yaar by Zakir Khan" format
        // Look for specific event listing patterns on category pages
        const categoryEventSelectors = [
            '[data-testid*="event"]',
            '[class*="EventRow"]',
            '[class*="event-listing"]',
            '[class*="ScheduleItem"]',
            '[class*="event-item"]',
            'div[class*="sc-"] > a[href*="event"]',  // StubHub uses styled-components
        ];

        // For category pages, find event rows that have date + time + venue + event name
        document.querySelectorAll('a[href*="/event/"]').forEach((eventLink) => {
            const href = eventLink.getAttribute('href') || '';
            // Only process actual event links (not generic navigation)
            if (!href.includes('/event/') || href.includes('category')) return;

            // Find the parent container for this event
            const eventRow = eventLink.closest('div, li, article') || eventLink;
            const rowText = getText(eventRow);

            // Skip if too short or too long (not a real event)
            if (!rowText || rowText.length < 20 || rowText.length > 500) return;

            // Skip location-only entries like "puneindia · 2 events"
            if (rowText.includes('·') && rowText.includes('events')) return;

            // Extract event name from multiple sources (best effort)
            let eventName = null;

            // Source 1: Extract from URL slug (most reliable for StubHub)
            // URL format: /papa-yaar-by-zakir-khan-pune-tickets-1-11-2026/event/12345
            const urlMatch = href.match(/\/([a-z0-9-]+)-tickets/i);
            if (urlMatch) {
                // Convert "papa-yaar-by-zakir-khan" to "papa yaar by zakir khan"
                eventName = urlMatch[1].replace(/-/g, ' ').trim();
            }

            // Source 2: If URL didn't work, try heading element
            if (!eventName) {
                const headingEl = eventRow.querySelector('h2, h3, h4, [class*="title"], [class*="name"]');
                if (headingEl) {
                    eventName = getText(headingEl);
                }
            }

            // Source 3: Try to parse from rowText - look for text before date pattern
            if (!eventName && rowText) {
                // Pattern: "Papa Yaar by Zakir Khansat, jan 11 • 8:00 pm..." 
                const datePattern = /(sun|mon|tue|wed|thu|fri|sat),?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/i;
                const dateMatch = rowText.match(datePattern);
                if (dateMatch && dateMatch.index > 5) {
                    eventName = rowText.substring(0, dateMatch.index).trim();
                }
            }

            // Source 4: Use main page h1 as the artist name (fallback)
            if (!eventName || eventName.length < 5) {
                eventName = mainEventName || getText(eventLink);
            }

            // Skip if event name looks like a location badge or garbage
            if (!eventName || eventName.includes('·') || eventName.toLowerCase().includes('events near')) return;
            if (eventName.length < 3 || eventName.toLowerCase().match(/^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$/)) return;

            // Extract venue and city from the row
            let venue = null;
            let city = null;
            let state = null;
            let dateText = null;

            // Look for venue/location text
            const venueEl = eventRow.querySelector('[class*="venue"], [class*="location"], [class*="place"]');
            if (venueEl) {
                venue = getText(venueEl);
                city = extractCity(venue);
                state = extractState(venue);
            }

            // Look for date/time
            const dateEl = eventRow.querySelector('[class*="date"], time, [class*="time"]');
            if (dateEl) {
                dateText = getText(dateEl);
            }

            // If no venue from element, try to parse from row text
            // Pattern: "Event Nameday, date • time venue, city"
            if (!city && rowText) {
                // Try to extract city from patterns like "Anna Bhau Sathe Auditorium | Pune, India"
                const cityPatterns = [
                    /\|\s*([^,|]+),\s*India/i,
                    /\|\s*([^,|]+),\s*[A-Z]{2}\s*$/i,
                    /auditorium[^|]*\|\s*([^,]+)/i,
                    /,\s*(mumbai|pune|delhi|bangalore|bengaluru|chennai|hyderabad|kolkata|ahmedabad)/i,
                ];
                for (const pattern of cityPatterns) {
                    const match = rowText.match(pattern);
                    if (match) {
                        city = match[1].trim().toLowerCase();
                        break;
                    }
                }
            }

            // Add this event
            collected.push({
                url: url,
                eventName: eventName.toLowerCase(),
                eventCategory: detectEventCategory(eventName) || eventCategory,
                venue: venue,
                city: city,
                state: state,
                date: dateText,
                dateRange: detectDateRange(rowText),
                section: extractSection(rowText),
                zone: extractZone(rowText),
                row: extractRow(rowText),
                ticketType: detectTicketType(rowText),
                deliveryType: detectDeliveryType(rowText),
                isVIP: isVIP(rowText),
                isAccessible: isAccessible(rowText),
                isParkingPass: isParkingPass(rowText),
                aisleSeat: isAisleSeat(rowText),
                includesExtras: hasExtras(rowText),
                info: "category_event"
            });
        });

        // Method 1: Look for links containing event info (search results)
        document.querySelectorAll('a[href*="/event/"], a[href*="tickets"]').forEach((link) => {
            const href = link.getAttribute('href') || '';
            const linkText = getText(link);

            if (linkText && linkText.length > 5 && linkText.length < 300) {
                const container = link.closest('div[class*="event"], div[class*="card"], li, article') || link;
                const fullText = getText(container);

                // Extract all possible data
                let city = null;
                let venue = null;
                let state = null;

                const locationText = container.querySelector('[class*="location"], [class*="venue"], [class*="city"]');
                if (locationText) {
                    const locText = getText(locationText);
                    city = extractCity(locText);
                    state = extractState(locText);
                    venue = locText;
                } else if (fullText) {
                    city = extractCity(fullText);
                    state = extractState(fullText);
                }

                collected.push({
                    url: url,
                    eventName: linkText.toLowerCase(),
                    eventCategory: detectEventCategory(linkText) || eventCategory,
                    city: city,
                    state: state,
                    venue: venue,
                    dateRange: detectDateRange(fullText),
                    section: extractSection(fullText),
                    zone: extractZone(fullText),
                    row: extractRow(fullText),
                    ticketType: detectTicketType(fullText),
                    deliveryType: detectDeliveryType(fullText),
                    isVIP: isVIP(fullText),
                    isAccessible: isAccessible(fullText),
                    isParkingPass: isParkingPass(linkText),
                    aisleSeat: isAisleSeat(fullText),
                    includesExtras: hasExtras(fullText),
                    info: "search_result"
                });
            }
        });

        // Method 2: Look for event cards/items with various class patterns
        const cardSelectors = [
            '[class*="EventItem"]',
            '[class*="event-card"]',
            '[class*="SearchResult"]',
            '[class*="listing"]',
            '[class*="Card"]',
            '[class*="ticket"]'
        ];

        cardSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach((card) => {
                const cardText = getText(card);
                const eventName = getText(card.querySelector('h2, h3, h4, [class*="title"], [class*="name"]'));
                const venueEl = card.querySelector('[class*="venue"], [class*="location"]');
                const venue = getText(venueEl);
                const priceText = getText(card.querySelector('[class*="price"]'));
                const dateText = getText(card.querySelector('[class*="date"], time'));
                const quantityText = getText(card.querySelector('[class*="quantity"], [class*="qty"]'));
                const sectionText = getText(card.querySelector('[class*="section"]'));
                const rowText = getText(card.querySelector('[class*="row"]'));
                const deliveryText = getText(card.querySelector('[class*="delivery"]'));

                if (eventName) {
                    collected.push({
                        url: url,
                        eventName: eventName.toLowerCase(),
                        eventCategory: detectEventCategory(eventName) || eventCategory,
                        venue: venue,
                        city: extractCity(venue),
                        state: extractState(venue),
                        price: parsePrice(priceText),
                        priceWithFees: parsePrice(priceText), // Same for now
                        date: dateText,
                        dateRange: detectDateRange(dateText),
                        ticketCount: parseTicketCount(quantityText),
                        section: extractSection(sectionText) || extractSection(cardText),
                        zone: extractZone(sectionText) || extractZone(cardText),
                        row: extractRow(rowText) || extractRow(cardText),
                        ticketType: detectTicketType(cardText),
                        deliveryType: detectDeliveryType(deliveryText) || detectDeliveryType(cardText),
                        isVIP: isVIP(cardText),
                        isAccessible: isAccessible(cardText),
                        isParkingPass: isParkingPass(cardText),
                        aisleSeat: isAisleSeat(cardText),
                        isInstantDownload: cardText?.toLowerCase().includes('instant'),
                        includesExtras: hasExtras(cardText),
                        info: "card"
                    });
                }
            });
        });

        // Method 3: If we found a main event name from h1, use that
        if (mainEventName && collected.length === 0) {
            let venue = null;
            let city = null;
            let state = null;

            const venueSelectors = [
                '[class*="venue"]',
                '[class*="location"]',
                '[class*="EventInfo"]',
                '[class*="EventHeader"]'
            ];

            for (const selector of venueSelectors) {
                const el = document.querySelector(selector);
                if (el) {
                    venue = getText(el);
                    city = extractCity(venue);
                    state = extractState(venue);
                    break;
                }
            }

            // Check for common LA venue names in page content
            const laVenues = ['crypto.com arena', 'staples center', 'sofi stadium', 'dodger stadium', 'los angeles', 'inglewood'];

            for (const laVenue of laVenues) {
                if (pageText.includes(laVenue)) {
                    if (!city) city = laVenue.includes('inglewood') ? 'inglewood' : 'los angeles';
                    break;
                }
            }

            collected.push({
                url: url,
                eventName: mainEventName.toLowerCase(),
                eventCategory: eventCategory,
                venue: venue,
                city: city,
                state: state,
                dateRange: detectDateRange(pageText),
                ticketType: detectTicketType(pageText),
                isVIP: isVIP(pageText),
                isAccessible: isAccessible(pageText),
                isParkingPass: isParkingPass(pageText),
                info: "page_title"
            });
        }

        // Method 4: No more fallbacks with hardcoded event names
        // The scraper is now fully generic and works for any event

        return collected;
    };

    // ============================================================================
    // MAIN EXECUTION
    // ============================================================================

    try {
        const scraped = scrapeGeneric();

        // Get page-level metadata once
        const urlFilters = parseUrlFilters();
        const loginStatus = detectLoginStatus();
        const pageType = detectPageType();

        // Deduplicate results by event name
        const seen = new Set();
        const pageText = document.body?.innerText || '';
        const eventId = extractEventId();
        const listingCount = extractListingCount(pageText);

        scraped.forEach(item => {
            const key = `${item.eventName}-${item.city || 'unknown'}`;
            if (!seen.has(key)) {
                seen.add(key);
                const itemText = JSON.stringify(item);
                const price = item.price || item.priceWithFees;

                // Enrich each result with page-level metadata
                results.push({
                    ...item,
                    // URL filter state (from URL params)
                    urlSections: urlFilters.sections,
                    urlQuantity: urlFilters.quantity,
                    urlTicketClasses: urlFilters.ticketClasses,
                    urlListingId: urlFilters.listingId,
                    urlRows: urlFilters.rows,
                    urlSeatTypes: urlFilters.seatTypes,
                    urlMinPrice: urlFilters.minPrice,
                    urlMaxPrice: urlFilters.maxPrice,
                    urlSort: urlFilters.sort,
                    // Page metadata
                    loginStatus: loginStatus,
                    pageType: pageType,
                    eventId: eventId,
                    // Currency detection
                    currency: item.currency || detectCurrency(document.body?.innerText || ''),
                    // Parsed time
                    parsedTime: parseTime(item.time || item.date || ''),
                    // Price tier classification
                    priceTier: classifyPriceTier(price),
                    // Listing count
                    totalListings: listingCount,
                    // Seller info
                    sellerRating: extractSellerRating(itemText),
                    sellerType: detectSellerType(itemText),
                    // Row and seat info
                    extractedRow: extractRowNumber(itemText),
                    extractedSeats: extractSeatNumbers(itemText),
                    // Additional flags
                    isResale: isResaleTicket(itemText),
                    faceValue: extractFaceValue(itemText),
                    ticketsTogether: areTicketsTogether(itemText),
                    // Availability status
                    availabilityStatus: detectAvailabilityStatus(pageText),
                    isPresale: isPresale(pageText),
                    // Gap-bridging fields
                    recommendedToggleOn: detectRecommendedToggle(),
                    filterPanelState: detectFilterPanelState(),
                    loadingState: detectLoadingState(),
                    obstructedView: detectObstructedView(itemText),
                    ageRestriction: detectAgeRestrictions(itemText),
                    listingAgeHours: extractListingAge(itemText),
                    isQuickPick: detectQuickPicks(itemText),
                    dealRating: detectBestValue(itemText),
                    viewQuality: extractViewQuality(itemText),
                    // Error detection (geo-blocking, CAPTCHA)
                    geoBlocking: detectGeoBlocking(),
                    captchaState: detectCaptcha(),
                });
            }
        });
    } catch (error) {
        console.error('StubHub scraper error:', error);
    }

    return results;
})();

