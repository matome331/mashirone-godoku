document.addEventListener('DOMContentLoaded', () => {
    const listContainer = document.getElementById('contentSections');
    const searchInput = document.getElementById('searchInput');
    const clearSearch = document.getElementById('clearSearch');
    const sortSelect = document.getElementById('sortSelect');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const noResults = document.getElementById('noResults');
    const kanaIndex = document.getElementById('kanaIndex');
    const backToTop = document.getElementById('backToTop');

    let allMisreadings = [];
    let displayedData = [];
    let currentLimit = 100;
    const ITEMS_PER_PAGE = 100;

    // Helper: Normalize text only for search matching.
    // Displayed text is left untouched.
    const normalizeSearchText = (value) => {
        return String(value ?? '')
            .normalize('NFKC')
            .replace(/[\u200B-\u200D\u2060\uFEFF]/g, '')
            .replace(/\s+/g, ' ')
            .trim()
            .toLowerCase();
    };

    // Helper: Parse HH:MM:SS to seconds
    const parseTimeToSeconds = (timeStr) => {
        if (!timeStr) return 0;
        const parts = timeStr.split(':').map(Number);
        if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
        if (parts.length === 2) return parts[0] * 60 + parts[1];
        return parts[0] || 0;
    };

    // Helper: Determine Kana Row
    const getKanaRow = (reading) => {
        if (!reading) return 'その他';
        const c = reading.charAt(0);
        if (/[あ-おぁ-ぉア-オァ-ォ]/.test(c)) return 'あ行';
        if (/[か-こが-ごカ-コガ-ゴ]/.test(c)) return 'か行';
        if (/[さ-そざ-ぞサ-ソザ-ゾ]/.test(c)) return 'さ行';
        if (/[た-とだ-どっタ-トダ-ドッ]/.test(c)) return 'た行';
        if (/[な-のナ-ノ]/.test(c)) return 'な行';
        if (/[は-ほば-ぼぱ-ぽハ-ホバ-ボパ-ポ]/.test(c)) return 'は行';
        if (/[ま-もマ-モ]/.test(c)) return 'ま行';
        if (/[や-よゃ-ょヤ-ヨャ-ョ]/.test(c)) return 'や行';
        if (/[ら-ろラ-ロ]/.test(c)) return 'ら行';
        if (/[わ-んゎワ-ンヮヴ]/.test(c)) return 'わ行';
        return 'その他';
    };

    // Helper: Sort function by timestamp (for inside same video)
    const sortByTimestamp = (a, b) => parseTimeToSeconds(a.timestamp) - parseTimeToSeconds(b.timestamp);

    // Load Data
    const loadData = () => {
        try {
            // dictionaryData (from data.js) を読み込む
            if (typeof dictionaryData !== 'undefined') {
                allMisreadings = dictionaryData;
            } else {
                throw new Error('dictionaryData is not defined');
            }

            displayedData = [...allMisreadings];

            loadingIndicator.classList.add('hidden');
            renderSections();
        } catch (error) {
            console.error('Data load error:', error);
            loadingIndicator.replaceChildren();
            const errorMessage = document.createElement('p');
            errorMessage.textContent = 'データの読み込みに失敗しました...😿';
            loadingIndicator.appendChild(errorMessage);
        }
    };

    // Rendering Logic
    const renderSections = () => {
        listContainer.replaceChildren();
        const sortMode = sortSelect.value;
        const fragment = document.createDocumentFragment();

        if (displayedData.length === 0) {
            noResults.classList.remove('hidden');
            kanaIndex.style.display = 'none';
            return;
        } else {
            noResults.classList.add('hidden');
        }

        // 検索中は全件表示、通常時はページング
        const isSearching = normalizeSearchText(searchInput.value) !== '';
        const visibleData = isSearching ? displayedData : displayedData.slice(0, currentLimit);
        let hasMoreFlag = !isSearching && currentLimit < displayedData.length;

        // --- GROUPING & SORTING LOGIC ---
        let groups = {};

        if (sortMode === 'kana') {
            // SHOW WIKI KANA INDEX
            kanaIndex.style.display = 'flex';

            const rowOrder = ['あ行', 'か行', 'さ行', 'た行', 'な行', 'は行', 'ま行', 'や行', 'ら行', 'わ行', 'その他'];
            const rowIndex = (item) => {
                const r = getKanaRow(item.reading);
                const idx = rowOrder.indexOf(r);
                return idx >= 0 ? idx : rowOrder.length;
            };

            // 全データを五十音順にソートしてからスライス
            const kanaSorted = [...displayedData].sort((a, b) => {
                const rowDiff = rowIndex(a) - rowIndex(b);
                if (rowDiff !== 0) return rowDiff;
                const rCompare = a.reading.localeCompare(b.reading, 'ja');
                if (rCompare !== 0) return rCompare;
                const dCompare = a.date.localeCompare(b.date);
                if (dCompare !== 0) return dCompare;
                return sortByTimestamp(a, b);
            });

            const visibleKana = isSearching ? kanaSorted : kanaSorted.slice(0, currentLimit);
            hasMoreFlag = !isSearching && currentLimit < kanaSorted.length;

            // Group by Kana Row
            visibleKana.forEach(item => {
                const row = getKanaRow(item.reading);
                if (!groups[row]) groups[row] = [];
                groups[row].push(item);
            });

            rowOrder.forEach(rowName => {
                if (!groups[rowName] || groups[rowName].length === 0) return;
                const section = createSectionGroup(rowName, '', groups[rowName], `row-${rowName.charAt(0)}`);
                fragment.appendChild(section);
            });

        } else {
            // HIDE KANA INDEX
            kanaIndex.style.display = 'none';

            // Group by Video (Date)
            visibleData.forEach(item => {
                const key = `${item.date}_${item.videoTitle}`;
                if (!groups[key]) groups[key] = { date: item.date, items: [] };
                groups[key].items.push(item);
            });

            // Convert groups to array and sort by Date
            const groupedArray = Object.values(groups);
            groupedArray.sort((a, b) => {
                const isADateValid = a.date && a.date !== '日付不明' && a.date !== 'NA';
                const isBDateValid = b.date && b.date !== '日付不明' && b.date !== 'NA';

                // Put unknown dates at the bottom always
                if (!isADateValid && isBDateValid) return 1;
                if (isADateValid && !isBDateValid) return -1;
                if (!isADateValid && !isBDateValid) return 0;

                return sortMode === 'dateDesc'
                    ? b.date.localeCompare(a.date)
                    : a.date.localeCompare(b.date);
            });

            groupedArray.forEach(group => {
                // Inside same video, ALWAYS sort by timestamp ascending
                const items = group.items.sort(sortByTimestamp);

                // Extract clean title without date suffix from the first item
                const cleanTitle = items[0].videoTitle;

                const section = createSectionGroup(cleanTitle, group.date, items, null);
                fragment.appendChild(section);
            });
        }

        listContainer.appendChild(fragment);

        // 「もっと見る」ボタン
        if (hasMoreFlag) {
            const remaining = displayedData.length - currentLimit;
            const loadMoreBtn = document.createElement('button');
            loadMoreBtn.className = 'load-more-btn';
            const loadMoreIcon = document.createElement('i');
            loadMoreIcon.className = 'fa-solid fa-chevron-down';
            loadMoreBtn.appendChild(loadMoreIcon);
            loadMoreBtn.appendChild(
                document.createTextNode(` もっと見る（残り ${remaining} 件）`)
            );
            loadMoreBtn.addEventListener('click', () => {
                currentLimit += ITEMS_PER_PAGE;
                renderSections();
            });
            listContainer.appendChild(loadMoreBtn);
        }
    };

    // Helper: Build DOM for a Section
    function createSectionGroup(headerTitle, dateText, itemsList, idAttribute) {
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'section-container';
        if (idAttribute) sectionDiv.id = idAttribute;

        // Header
        const header = document.createElement('h2');
        header.className = 'section-header';

        // If sorting by date, show date subtly
        if (dateText) {
            const titleSpan = document.createElement('span');
            titleSpan.className = 'section-title-text';
            titleSpan.textContent = headerTitle;

            const dateSpan = document.createElement('span');
            dateSpan.className = 'section-date';
            dateSpan.textContent = dateText;

            header.append(titleSpan, dateSpan);
        } else {
            header.textContent = headerTitle;
        }
        sectionDiv.appendChild(header);

        // Grid List
        const ul = document.createElement('ul');
        ul.className = 'card-grid';

        itemsList.forEach((item) => {
            const li = document.createElement('li');
            li.className = 'misreading-card';

            const cardLeft = document.createElement('div');
            cardLeft.className = 'card-left';

            const timestamp = document.createElement('div');
            timestamp.className = 'timestamp';
            timestamp.textContent = item.date;

            const words = document.createElement('div');
            words.className = 'words';

            const original = document.createElement('span');
            original.className = 'original';
            original.textContent = item.original;

            const reading = document.createElement('span');
            reading.className = 'reading';
            reading.textContent = `(${item.reading})`;

            words.append(original, reading);

            const videoContext = document.createElement('div');
            videoContext.className = 'video-context';
            videoContext.textContent = item.videoTitle;
            videoContext.title = item.videoTitle;

            cardLeft.append(timestamp, words, videoContext);

            const playLink = document.createElement('a');
            playLink.href = item.videoUrl;
            playLink.target = '_blank';
            playLink.rel = 'noopener noreferrer';
            playLink.className = 'play-btn';
            playLink.setAttribute('aria-label', 'YouTubeで再生');

            const playIcon = document.createElement('i');
            playIcon.className = 'fa-solid fa-play';
            playLink.appendChild(playIcon);

            li.append(cardLeft, playLink);
            ul.appendChild(li);
        });

        sectionDiv.appendChild(ul);
        return sectionDiv;
    };

    // --- Events ---

    // Sort change
    sortSelect.addEventListener('change', () => {
        currentLimit = ITEMS_PER_PAGE;
        renderSections();
        window.scrollTo(0, 0);
    });

    // Search logic
    const handleSearch = (e) => {
        const term = normalizeSearchText(e.target.value);
        currentLimit = ITEMS_PER_PAGE;
        if (term === '') {
            displayedData = [...allMisreadings];
        } else {
            displayedData = allMisreadings.filter(item => {
                // 表示文字列は変更せず、検索時だけ正規化して比較する。
                const original = normalizeSearchText(item.original);
                const reading = normalizeSearchText(item.reading);
                return original.includes(term) || reading.includes(term);
            });
        }
        renderSections();
    };

    let timeoutId;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => handleSearch(e), 200);
    });

    clearSearch.addEventListener('click', () => {
        searchInput.value = '';
        searchInput.dispatchEvent(new Event('input'));
        searchInput.focus();
    });

    // 五十音インデックスのクリック → 全件読み込んでからジャンプ
    kanaIndex.addEventListener('click', (e) => {
        const link = e.target.closest('a');
        if (!link) return;
        e.preventDefault();

        // 全件表示にして対象セクションを確実にDOMに存在させる
        currentLimit = displayedData.length;
        renderSections();

        // ジャンプ先へスクロール
        const targetId = link.getAttribute('href').substring(1);
        const targetEl = document.getElementById(targetId);
        if (targetEl) {
            targetEl.scrollIntoView({ behavior: 'smooth' });
        }
    });

    // Back to top behavior
    window.addEventListener('scroll', () => {
        if (window.scrollY > 300) {
            backToTop.classList.remove('hidden');
        } else {
            backToTop.classList.add('hidden');
        }
    });

    backToTop.addEventListener('click', (e) => {
        e.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // --- Title Hover Effect (Custom Tooltip follow mouse) ---
    const titleArea = document.querySelector('.title-area');
    const subtitle = document.querySelector('.subtitle');

    if (titleArea && subtitle) {
        titleArea.addEventListener('mousemove', (e) => {
            // マウスの右下にビタビタに配置
            subtitle.style.left = (e.clientX + 2) + 'px';
            subtitle.style.top = (e.clientY + 2) + 'px';
        });
    }

    // Run
    loadData();
});
