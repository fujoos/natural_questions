// Dynamically determine the API URL based on the current location
let apiUrl;
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    apiUrl = '/data'; // Use the localhost server when running locally
} else {
    apiUrl = 'https://your-deployed-domain.com/data'; // Use the deployed server URL when running in production
}

const RUN_ID = "{{ run_id }}";

// Global variable to track the current page
let currentPaginationPage = 1;

// On document ready, set up event listeners and fetch initial data
$(document).ready(function () {
    const storedRunId = localStorage.getItem('runId');

    // If the run ID has changed (indicating a new run), clear the storage
    if (storedRunId !== RUN_ID) {
        console.log('New run detected, clearing local storage...');
        localStorage.clear();  // Clears the entire localStorage
        sessionStorage.clear();  // Clears the entire sessionStorage

        // Update the stored run ID to the current ID
        localStorage.setItem('runId', RUN_ID);
    }

    fetchData();

    // Event listener for dataset selector change
    $('#csv-selector, #page-size').change(function () {
        currentPaginationPage = 1; // Reset to page 1 when data or page size changes
        fetchData(); // Fetch data for the new dataset or page size
    });


    // Pagination control click handler
    $('body').on('click', '.page-link', function (e) {
        e.preventDefault(); // Prevent default link behavior
        const page = $(this).data('page'); // Get the page number from the clicked link
        currentPaginationPage = page; // Update the global page tracker
        fetchData(page); // Fetch data for the new page
    });

});
// Refresh button event listener to clear cache and fetch new data
document.addEventListener('DOMContentLoaded', function () {
    const refreshButton = document.getElementById('refresh-data');
    refreshButton.addEventListener('click', function () {
        clearCurrentPageCache(); // Clear cache for the current view
        fetchData(currentPaginationPage); // Fetch new data
    });
});

// Function to clear cache for the current page and settings
function clearCurrentPageCache() {
    const selectedFile = $('#csv-selector').val();
    const pageSize = parseInt($('#page-size').val(), 10);
    const cacheKey = generateCacheKey(selectedFile, currentPaginationPage, pageSize);
    sessionStorage.removeItem(cacheKey); // Remove the specific cache entry
    console.log(`Cache cleared for key: ${cacheKey}`); // Log cache clearance for debugging
}

// Main function to fetch data, with optional page parameter defaulting to the current page
async function fetchData(page = currentPaginationPage) {
    const selectedFile = $('#csv-selector').val(); // Get selected dataset
    const pageSize = parseInt($('#page-size').val(), 10); // Get selected page size
    const cacheKey = generateCacheKey(selectedFile, page, pageSize); // Generate a unique cache key

    let data; // Declare data outside try-catch for broader scope

    try {
        data = sessionStorage.getItem(cacheKey); // Attempt to retrieve cached data
        if (!data) {
            showLoadingIndicator(); // Show loading indicator if fetching new data
            const response = await fetch(`${apiUrl}?file_id=${selectedFile}&page=${page}&page_size=${pageSize}`);

            if (!response.ok) {
                console.error('Failed to load data'); // Log error instead of throwing
                // Optionally, handle this error by showing a message to the user or retrying the fetch
                return; // Exit the function or handle the error as appropriate
            }

            data = await response.json();

            try {
                sessionStorage.setItem(cacheKey, JSON.stringify(data)); // Attempt to cache the new data
                console.log(`Data cached for key: ${cacheKey}`); // Log data caching
            } catch (e) {
                if (isQuotaExceeded(e)) { // Check if the error is due to exceeding storage limits
                    console.warn("Storage limit reached. Not caching this data.", e); // Warn about storage limits
                } else {
                    console.error("Error caching data:", e); // Log unexpected caching errors
                }
            }
        } else {
            data = JSON.parse(data); // Parse the cached JSON data
            console.log(`Using cached data for key: ${cacheKey}`); // Log usage of cached data
        }

        // Wait for updateTable to complete before updating pagination
        updatePagination(data.currentPage, data.totalPages); // Update pagination controls
        await updateTable(data.data, data.currentPage, data.pageSize);

    } catch (error) {
        console.error("Error fetching or processing data:", error); // Handle unexpected errors
    } finally {
        hideLoadingIndicator(); // Ensure loading indicator is hidden after operation
    }
}

async function fetchDataAsync() {
    try {
        await fetchData(); // Assuming fetchData() does not need arguments, or you have provided them
        // Code here runs after fetchData completes
    } catch (error) {
        // Handle errors from fetchData
        console.error("Error in fetchData:", error);
    }
}


// Function to generate a unique cache key incorporating run ID, file ID, page, and page size
function generateCacheKey(fileId, page, pageSize) {
    return `parquetData-${RUN_ID}-${fileId}-${page}-${pageSize}`;
}

function updateTable(data, currentPage, pageSize) {
    return new Promise((resolve) => {
        const tableBody = $('#data-rows');
        tableBody.empty(); // Clear existing table rows

        data.forEach(function (row, index) {
            const tr = $('<tr>');
            // Calculate the correct index considering the current page and page size
            const rowIndex = ((currentPage - 1) * pageSize) + (index + 1);
            // Format rowIndex with a thousand separator
            const formattedRowIndex = rowIndex.toLocaleString(); // Uses the browser's locale to format

            // Append the row index and question
            tr.append(`<td>${formattedRowIndex}</td>`);
            tr.append(`<td>${row["question"]}</td>`);

            // Handle long answers with potential inner tables
            if (row["long_answers"].trim()) {
                tr.append(`<td>${row["long_answers"]}</td>`);
            } else {
                tr.append(`<td></td>`);
            }

            // Check if 'short_answers' is empty and handle accordingly
            if (row["short_answers"].trim()) {
                tr.append(`<td>${row["short_answers"]}</td>`);
            } else {
                // If empty, you could add a placeholder or leave it blank
                tr.append('<td></td>'); // Option to add a placeholder
                // tr.append('<td></td>'); // Option to leave the cell blank
            }

            tableBody.append(tr);
        });
        resolve(); // Resolve the promise once the update is complete
    });
}

function updatePagination(currentPage, totalPages) {
    console.log('pagination construction started')
    const paginationContainer = $('.pagination');
    paginationContainer.empty(); // Clear existing pagination buttons

    // Add 'First' button
    paginationContainer.append(`<li class="page-item ${currentPage === 1 ? 'disabled' : ''}"><a class="page-link" href="#" data-page="1">First</a></li>`);

    // Add 'Previous' button
    paginationContainer.append(`<li class="page-item ${currentPage === 1 ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage - 1}">Previous</a></li>`);

    // Determine page numbers to display
    let startPage = Math.max(currentPage - 2, 1);
    let endPage = startPage + 4; // Display 5 pages at most
    if (endPage > totalPages) {
        endPage = totalPages;
        startPage = Math.max(endPage - 4, 1);
    }

    // Add page number buttons
    for (let i = startPage; i <= endPage; i++) {
        paginationContainer.append(`<li class="page-item ${i === currentPage ? 'active' : ''}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`);
    }

    // Add 'Next' button
    paginationContainer.append(`<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${currentPage + 1}">Next</a></li>`);

    // Add 'Last' button
    paginationContainer.append(`<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}"><a class="page-link" href="#" data-page="${totalPages}">Last</a></li>`);
}

function showLoadingIndicator() {
    $('#table-overlay').show(); // Show the table overlay
    $('#loading-indicator').show(); // Show the progress bar
    simulateProgressBar(); // Start simulating progress bar
}

function hideLoadingIndicator() {
    $('#table-overlay').hide(); // Hide the table overlay
    $('#loading-indicator').hide(); // Hide the progress bar
    // Reset progress bar width
    $('#loading-indicator .progress-bar').css('width', '0%').attr('aria-valuenow', 0);
}

let progressInterval; // Declare the interval variable outside the function scope

function simulateProgressBar() {
    clearInterval(progressInterval); // Clear any existing interval to avoid overlaps
    let progress = 0;
    progressInterval = setInterval(function () {
        progress += 10; // Increment progress
        if (progress <= 100) {
            $('#loading-indicator .progress-bar').css('width', progress + '%').attr('aria-valuenow', progress);
        } else {
            clearInterval(progressInterval); // Stop the interval when progress reaches 100%
        }
    }, 100); // Update every 100ms
}


function isQuotaExceeded(e) {
    let quotaExceeded = false;
    if (e) {
        if (e.code) {
            switch (e.code) {
                case 22:
                    quotaExceeded = true;
                    break;
                case 1014: // Firefox
                    if (e.name === 'NS_ERROR_DOM_QUOTA_REACHED') {
                        quotaExceeded = true;
                    }
                    break;
            }
        } else if (e.number === -2147024882) { // Internet Explorer 8
            quotaExceeded = true;
        }
    }
    return quotaExceeded;
}