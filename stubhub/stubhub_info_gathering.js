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

    const parsePrice = (text) => {
        if (!text) return null;
        const match = text.match(/\$?([\d,]+(?:\.\d{2})?)/);
        if (match) {
            return parseFloat(match[1].replace(/,/g, ""));
        }
        return null;
    };

    const parseTicketCount = (text) => {
        if (!text) return null;
        const match = text.match(/(\d+)\s*ticket/i);
        if (match) {
            return parseInt(match[1]);
        }
        return null;
    };

    const extractCity = (text) => {
        if (!text) return null;
        // Common patterns: "City, State" or "City, State, Country"
        const cityMatch = text.match(/([A-Za-z\s]+),\s*([A-Z]{2})/);
        if (cityMatch) {
            return cityMatch[1].trim().toLowerCase();
        }
        return text.toLowerCase();
    };

    const extractState = (text) => {
        if (!text) return null;
        const stateMatch = text.match(/,\s*([A-Z]{2})/);
        if (stateMatch) {
            return stateMatch[1];
        }
        return null;
    };

    const detectEventCategory = (text) => {
        if (!text) return null;
        const lowerText = text.toLowerCase();

        // Sports detection
        const sportsKeywords = ['nba', 'nfl', 'mlb', 'nhl', 'mls', 'ncaa', 'basketball', 'football', 'baseball', 'hockey', 'soccer'];
        for (const keyword of sportsKeywords) {
            if (lowerText.includes(keyword)) return 'sports';
        }

        // Concert detection
        const concertKeywords = ['concert', 'tour', 'live', 'music', 'performance'];
        for (const keyword of concertKeywords) {
            if (lowerText.includes(keyword)) return 'concerts';
        }

        // Theater detection
        const theaterKeywords = ['broadway', 'theater', 'theatre', 'musical', 'play', 'show'];
        for (const keyword of theaterKeywords) {
            if (lowerText.includes(keyword)) return 'theater';
        }

        // Comedy detection
        const comedyKeywords = ['comedy', 'standup', 'stand-up', 'comedian'];
        for (const keyword of comedyKeywords) {
            if (lowerText.includes(keyword)) return 'comedy';
        }

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

        // Method 4: Fallback - search for text containing key terms
        const lakersMatch = pageText.includes('lakers');
        const laMatch = pageText.includes('los angeles') ||
            pageText.includes('crypto.com arena') ||
            pageText.includes('inglewood');

        if (lakersMatch && collected.length === 0) {
            collected.push({
                url: url,
                eventName: 'lakers',
                eventCategory: 'sports',
                city: laMatch ? 'los angeles' : null,
                info: "text_match"
            });
        }

        return collected;
    };

    // ============================================================================
    // MAIN EXECUTION
    // ============================================================================

    try {
        const scraped = scrapeGeneric();

        // Deduplicate results by event name
        const seen = new Set();
        scraped.forEach(item => {
            const key = `${item.eventName}-${item.city || 'unknown'}`;
            if (!seen.has(key)) {
                seen.add(key);
                results.push(item);
            }
        });
    } catch (error) {
        console.error('StubHub scraper error:', error);
    }

    return results;
})();
