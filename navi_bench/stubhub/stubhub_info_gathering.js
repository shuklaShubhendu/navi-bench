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

    // ============================================================================
    // GENERIC SCRAPER - Works on any StubHub page
    // ============================================================================

    const scrapeGeneric = () => {
        const collected = [];

        // Try to get the main event title from h1 or title
        const h1 = document.querySelector('h1');
        const pageTitle = document.title;
        let mainEventName = getText(h1) || pageTitle?.split(' | ')[0] || null;

        // Clean up event name
        if (mainEventName) {
            mainEventName = mainEventName
                .replace(/tickets$/i, '')
                .replace(/\s+/g, ' ')
                .trim()
                .toLowerCase();
        }

        // Method 1: Look for links containing event info (search results)
        document.querySelectorAll('a[href*="/event/"], a[href*="tickets"]').forEach((link) => {
            const href = link.getAttribute('href') || '';
            const linkText = getText(link);

            if (linkText && linkText.length > 5 && linkText.length < 200) {
                // Try to extract event info from the link or its container
                const container = link.closest('div[class*="event"], div[class*="card"], li, article') || link;
                const fullText = getText(container);

                // Look for city/location info
                let city = null;
                const locationText = container.querySelector('[class*="location"], [class*="venue"], [class*="city"]');
                if (locationText) {
                    city = extractCity(getText(locationText));
                } else if (fullText) {
                    city = extractCity(fullText);
                }

                collected.push({
                    url: url,
                    eventName: linkText.toLowerCase(),
                    city: city,
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
            '[class*="Card"]'
        ];

        cardSelectors.forEach(selector => {
            document.querySelectorAll(selector).forEach((card) => {
                const eventName = getText(card.querySelector('h2, h3, h4, [class*="title"], [class*="name"]'));
                const venue = getText(card.querySelector('[class*="venue"], [class*="location"]'));
                const priceText = getText(card.querySelector('[class*="price"]'));
                const dateText = getText(card.querySelector('[class*="date"], time'));

                if (eventName) {
                    collected.push({
                        url: url,
                        eventName: eventName.toLowerCase(),
                        venue: venue,
                        city: extractCity(venue),
                        price: parsePrice(priceText),
                        date: dateText,
                        info: "card"
                    });
                }
            });
        });

        // Method 3: If we found a main event name from h1, use that
        if (mainEventName && collected.length === 0) {
            // Look for venue/location anywhere on the page
            let venue = null;
            let city = null;

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
                    break;
                }
            }

            // Also check for common LA venue names in page content
            const pageText = document.body?.innerText?.toLowerCase() || '';
            const laVenues = ['crypto.com arena', 'staples center', 'sofi stadium', 'dodger stadium', 'los angeles', 'inglewood'];

            for (const laVenue of laVenues) {
                if (pageText.includes(laVenue)) {
                    if (!city) city = laVenue.includes('inglewood') ? 'inglewood' : 'los angeles';
                    break;
                }
            }

            collected.push({
                url: url,
                eventName: mainEventName,
                venue: venue,
                city: city,
                info: "page_title"
            });
        }

        // Method 4: Search for text containing key terms
        const allText = document.body?.innerText || '';
        const lakersMatch = allText.toLowerCase().includes('lakers');
        const laMatch = allText.toLowerCase().includes('los angeles') ||
            allText.toLowerCase().includes('crypto.com arena') ||
            allText.toLowerCase().includes('inglewood');

        if (lakersMatch && collected.length === 0) {
            collected.push({
                url: url,
                eventName: 'lakers',
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
