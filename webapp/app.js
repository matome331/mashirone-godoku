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
            loadingIndicator.innerHTML = '<p>データの読み込みに失敗しました...😿</p>';
        }
    };

    // Rendering Logic
    const renderSections = () => {
        listContainer.innerHTML = '';
        const sortMode = sortSelect.value;
        const fragment = document.createDocumentFragment();

        if (displayedData.length === 0) {
            noResults.classList.remove('hidden');
            kanaIndex.style.display = 'none';
            return;
        } else {
            noResults.classList.add('hidden');
        }

        // --- GROUPING & SORTING LOGIC ---
        let groups = {};

        if (sortMode === 'kana') {
            // SHOW WIKI KANA INDEX
            kanaIndex.style.display = 'flex';

            // Group by Kana Row
            displayedData.forEach(item => {
                const row = getKanaRow(item.reading);
                if (!groups[row]) groups[row] = [];
                groups[row].push(item);
            });

            const rowOrder = ['あ行', 'か行', 'さ行', 'た行', 'な行', 'は行', 'ま行', 'や行', 'ら行', 'わ行', 'その他'];

            rowOrder.forEach(rowName => {
                if (!groups[rowName] || groups[rowName].length === 0) return;

                // Sort inside row: Alphabetical by reading -> Date -> Timestamp
                const items = groups[rowName].sort((a, b) => {
                    const rCompare = a.reading.localeCompare(b.reading, 'ja');
                    if (rCompare !== 0) return rCompare;
                    // 同じ読みなら、日付が古い順（昇順）に並べる
                    const dCompare = a.date.localeCompare(b.date);
                    if (dCompare !== 0) return dCompare;
                    // 日付まで同じなら、タイムスタンプ順（昇順）
                    return sortByTimestamp(a, b);
                });

                const section = createSectionGroup(rowName, '', items, `row-${rowName.charAt(0)}`);
                fragment.appendChild(section);
            });

        } else {
            // HIDE KANA INDEX
            kanaIndex.style.display = 'none';

            // Group by Video (Date)
            displayedData.forEach(item => {
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
            header.innerHTML = `<span class="section-title-text">${headerTitle}</span><span class="section-date">${dateText}</span>`;
        } else {
            header.textContent = headerTitle;
        }
        sectionDiv.appendChild(header);

        // Grid List
        const ul = document.createElement('ul');
        ul.className = 'card-grid';

        itemsList.forEach((item, index) => {
            const li = document.createElement('li');
            li.className = 'misreading-card';

            li.innerHTML = `
                <div class="card-left">
                    <div class="timestamp">${item.date}</div>
                    <div class="words">
                        <span class="original">${item.original}</span>
                        <span class="reading">(${item.reading})</span>
                    </div>
                    <div class="video-context" title="${item.videoTitle}">${item.videoTitle}</div>
                </div>
                <a href="${item.videoUrl}" target="_blank" rel="noopener noreferrer" class="play-btn" aria-label="YouTubeで再生">
                    <i class="fa-solid fa-play"></i>
                </a>
            `;
            ul.appendChild(li);
        });

        sectionDiv.appendChild(ul);
        return sectionDiv;
    };

    // --- Events ---

    // Sort change
    sortSelect.addEventListener('change', () => {
        renderSections();
        window.scrollTo(0, 0);
    });

    // Search logic
    const handleSearch = (e) => {
        const term = e.target.value.toLowerCase().trim();
        if (term === '') {
            displayedData = [...allMisreadings];
        } else {
            displayedData = allMisreadings.filter(item => {
                // 誤読そのもの（原文）と読み方のみを検索対象にする
                return item.original.toLowerCase().includes(term) ||
                    item.reading.toLowerCase().includes(term);
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
