// Dynamically determine the API URL based on the current location
let apiUrl;
if (
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
) {
    apiUrl = "/data"; // Use the localhost server when running locally
} else {
    apiUrl = "https://fujoos.pythonanywhere.com/data"; // Use the deployed server URL when running in production
}

// Global variable to track the current page
let currentPaginationPage = 1;

// On document ready, set up event listeners and fetch initial data
$(document).ready(async function () {
    // Function to toggle dark mode
    // Function to toggle dark mode
    const toggleDarkMode = (enable) => {
        $("body").toggleClass("dark-mode", enable);
        $("#darkModeToggle").prop("checked", enable);
        localStorage.setItem("darkMode", enable);
        updateIframeStylesForDarkMode(enable); // Ensure iframes are updated accordingly
    };

    // Check system preference and previously saved user preference
    const prefersDarkMode = window.matchMedia(
        "(prefers-color-scheme: dark)",
    ).matches;
    const storedDarkMode = localStorage.getItem("darkMode");
    const isDarkMode =
        storedDarkMode !== null ? storedDarkMode === "true" : prefersDarkMode;

    // Apply dark mode based on the resolved preference
    toggleDarkMode(isDarkMode);

    // Listener for system color scheme changes
    window.matchMedia("(prefers-color-scheme: dark)").addListener((e) => {
        // Update dark mode only if user hasn't manually set a preference
        if (localStorage.getItem("darkMode") === null) {
            toggleDarkMode(e.matches);
        }
    });

    // Event listener for the dark mode toggle checkbox
    $("#darkModeToggle").on("change", function () {
        toggleDarkMode(this.checked);
    });
    const storedRunId = localStorage.getItem("runId");

    // If the run ID has changed (indicating a new run), clear the storage
    if (storedRunId !== RUN_ID) {
        //console.log("New run detected, clearing local storage...");
        localStorage.clear(); // Clears the entire localStorage
        sessionStorage.clear(); // Clears the entire sessionStorage

        // Update the stored run ID to the current ID
        localStorage.setItem("runId", RUN_ID);
    }

    await fetchData();

    // Event listener for dataset selector change
    $("#csv-selector, #page-size").change(async function () {
        currentPaginationPage = 1; // Reset to page 1 when data or page size changes
        await fetchData(); // Fetch data for the new dataset or page size
    });

    // Pagination control click handler
    $("body").on("click", ".top-pagination .page-link", async function (e) {
        e.preventDefault(); // Prevent default link behavior
        const page = $(this).data("page"); // Get the page number from the clicked link
        currentPaginationPage = page; // Update the global page tracker
        await fetchData(page); // Fetch data for the new page
    });

    // Show the button when the user scrolls down 20px from the top of the document
    window.onscroll = function () {
        if (
            document.body.scrollTop > 20 ||
            document.documentElement.scrollTop > 20
        ) {
            document.getElementById("scrollToTopBtn").style.display = "block";
        } else {
            document.getElementById("scrollToTopBtn").style.display = "none";
        }
    };

    // When the user clicks the button, scroll to the top of the document smoothly
    document.getElementById("scrollToTopBtn").onclick = function () {
        window.scrollTo({top: 0, behavior: "smooth"});
    };

    // Call the iframe optimization functions after the iframes are potentially added to the DOM
    enhanceIframeSecurity();
    lazyLoadIframes();
    improveIframeAccessibility();
});

// Lazy Load iFrames
function lazyLoadIframes() {
    const iframes = document.querySelectorAll('iframe[data-src]'); // Use data-src attribute for lazy loading
    // Configuration for the intersection observer
    const config = {
        rootMargin: '100px 0px', // Load iframes when they are within 100px of the viewport
        threshold: 0.01 // Trigger as soon as 1% of the iframe is visible
    };

    let observer = new IntersectionObserver(function (entries, observer) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const iframe = entry.target;
                iframe.src = iframe.dataset.src; // Set the actual source from data-src
                observer.unobserve(iframe); // Stop observing the iframe once it's loaded
            }
        });
    }, config);

    iframes.forEach(iframe => {
        observer.observe(iframe); // Start observing each iframe
    });
}

// Enhance Iframe Security with Sand-boxing
function enhanceIframeSecurity() {
    $("iframe").each(function () {
        $(this).attr('sandbox', 'allow-scripts allow-same-origin allow-forms'); // Apply sandbox policies here
    });
}

// Improve Accessibility of iFrames
function improveIframeAccessibility() {
  $("iframe").each(function (index) {
    $(this).attr('title', 'Iframe Content ' + (index + 1)); // Set a descriptive title for each iframe
  });
}
// Refresh button event listener to clear cache and fetch new data
    document.addEventListener("DOMContentLoaded", function () {
        const refreshButton = document.getElementById("refresh-data");
        refreshButton.addEventListener("click", async function () {
            const icon = this.querySelector(".icon-refresh"); // Assuming the icon has the class 'refresh-icon'
            icon.classList.add("icon-clicked");
            clearCurrentPageCache(); // Clear cache for the current view
            await fetchData(currentPaginationPage); // Fetch new data
            icon.classList.remove("icon-clicked");
        });
    });

// Function to clear cache for the current page and settings
    function clearCurrentPageCache() {
        const selectedFile = $("#csv-selector").val();
        const pageSize = parseInt($("#page-size").val(), 10);
        const cacheKey = generateCacheKey(
            selectedFile,
            currentPaginationPage,
            pageSize,
        );
        sessionStorage.removeItem(cacheKey); // Remove the specific cache entry
        //console.log(`Cache cleared for key: ${cacheKey}`); // Log cache clearance for debugging
    }

    /**
     * Fetches data from an API or cache, updates the UI with the fetched data, and handles pagination.
     * @param {number} page - The current page number to fetch, defaults to the global currentPaginationPage.
     */
    async function fetchData(page = currentPaginationPage) {
        try {
            // Hide or reset and Show the loading indicator to inform the user that data is being fetched.
            hideLoadingIndicator();
            showLoadingIndicator();

            // Retrieve the selected dataset and page size from the UI.
            const selectedFile = $("#csv-selector").val();
            const pageSize = parseInt($("#page-size").val(), 10);

            // Generate a unique cache key based on the selected file, current page, and page size.
            const cacheKey = generateCacheKey(selectedFile, page, pageSize);

            // Attempt to retrieve the cached data from sessionStorage.
            let data = sessionStorage.getItem(cacheKey);

            // If there is no cached data, fetch it from the API.
            if (!data) {
                // Construct the API URL with query parameters.
                const response = await fetch(
                    `${apiUrl}?table_name=${selectedFile}&page=${page}&page_size=${pageSize}`,
                );

                // Check if the response was successful.
                if (!response.ok) throw new Error("Failed to fetch data from the API.");

                // Parse the JSON response.
                data = await response.json();

                // Cache the fetched data to avoid unnecessary future API requests.
                sessionStorage.setItem(cacheKey, JSON.stringify(data));
            } else {
                // If cached data is found, parse it from JSON.
                data = JSON.parse(data);
            }

            // Validate the structure of the fetched or cached data.
            if (
                !data ||
                typeof data.currentPage === "undefined" ||
                typeof data.totalPages === "undefined" ||
                !Array.isArray(data.data)
            ) {
                throw new Error("Invalid or corrupt data structure received.");
            }

            // Update the UI pagination controls based on the current page and total pages.
            await updatePagination(data.currentPage, data.totalPages);

            // Update the data table in the UI with the fetched data.
            await updateTable(data.data, data.currentPage, data.pageSize);
        } catch (error) {
            // Log and handle any errors that occurred during the fetch or processing.
            console.error("Error fetching or processing data:", error);
            // Implement error handling UI feedback here (e.g., error messages to the user).
        } finally {
            // Hide the loading indicator now that data fetching and processing are complete.
            completeProgressBar();
        }
    }

// Function to generate a unique cache key incorporating run ID, file ID, page, and page size
    function generateCacheKey(fileId, page, pageSize) {
        return `parquetData-${RUN_ID}-${fileId}-${page}-${pageSize}`;
    }

// Define your CSS as a template
//     const iframeCssTemplate = `
// <style>
//
// @font-face {
//   font-family: 'Satoshi-Variable';
//   src: url('/static/fonts/Satoshi/Satoshi-Variable.woff2') format('woff2'),
//        url('/static/fonts/Satoshi/Satoshi-Variable.woff') format('woff'),
//        url('/static/fonts/Satoshi/Satoshi-Variable.ttf') format('truetype');
//   font-weight: 300 900; /* Range of weight this font supports */
//   font-display: swap;
//   font-style: normal;
// }
//
//   /* Add Bootstrap CSS from CDN */
//   @import url('/static/src/bootstrap.min.css');
//
//   /* Your existing styles */
//   body { font-family: 'Satoshi-Variable', sans-serif;  font-variation-settings: 'wght' 400; margin; 0; font-size: 15px; line-height: 1.5; color: #0F1111; -webkit-font-smoothing: antialiased;
//     -moz-osx-font-smoothing: grayscale;
//     text-rendering: optimizeLegibility;
//     -webkit-tap-highlight-color: transparent;}
//   p {margin: 0;}
//   table { width: 100%; height:auto; border-collapse: collapse; color: #0F1111;}
//   th, td { font-family: 'Satoshi-Variable', sans-serif; font-variation-settings: 'wght' 400; -moz-osx-font-smoothing: grayscale;
//     text-rendering: optimizeLegibility;
//     -webkit-tap-highlight-color: transparent; border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 15px; line-height: 1.5; color: #0F1111;}}
//   ::-webkit-scrollbar { width: 5px; height: 5px; }
//   ::-webkit-scrollbar-track { background: #f1f1f1; }
//   ::-webkit-scrollbar-thumb { background: #888; }
//   ::-webkit-scrollbar-thumb:hover { background: #555; }
//
//   /* Dark mode styles */
//   body.dark-mode { margin: 0; background-color: #0a0a0a; color: rgb(255, 255, 255, 0.5); -webkit-font-smoothing: antialiased;
//     -moz-osx-font-smoothing: grayscale;
//     text-rendering: optimizeLegibility;
//     -webkit-tap-highlight-color: transparent;}
//   body.dark-mode th, body.dark-mode td { border-color: #0F1111; color: rgb(255, 255, 255, 0.5); }
// </style>
// `;

    function updateIframeStylesForDarkMode(isDarkMode) {
        $("iframe").each(function () {
            const iframeDoc = this.contentDocument || this.contentWindow.document;
            $(iframeDoc.body).toggleClass("dark-mode", isDarkMode);
        });
    }

// Update the toggle click handler
    $("#darkModeToggle").click(function () {
        const isDarkMode = $(this).is(":checked");
        updateIframeStylesForDarkMode(isDarkMode);
    });

    function updateTable(data, currentPage, pageSize) {
        return new Promise((resolve) => {
            const tableBody = $("#data-rows");
            tableBody.empty(); // Clear existing table rows

            // Check if dark mode is currently enabled on the main document
            const isDarkMode = $("body").hasClass("dark-mode");

            // Loop through each data item and create table rows
            data.forEach(function (row, index) {
                const tr = $("<tr>");

                // Calculate the correct index considering the current page and page size
                const rowIndex = (
                    (currentPage - 1) * pageSize +
                    (index + 1)
                ).toLocaleString();

                // Append the row index and question
                tr.append(`<td>${rowIndex}</td>`);
                tr.append(`<td>${row["question"]}</td>`);

                // Check if the row has long answers and needs an iframe to display them
                if (row["long_answers"].trim()) {
                    // Construct the srcdoc for the iframe with dark mode styles included if necessary
                    const iframeSrcdoc = `
          <link rel="stylesheet" href="/static/src/bootstrap.min.css">
          <link rel="stylesheet" href="/static/src/custom.min.css">
          <body class="${isDarkMode ? "dark-mode" : ""}">
            ${row["long_answers"]}
          </body>
        `;

                    // Create the iframe element with the constructed srcdoc
                    const iframe = $("<iframe />", {
                        style: "width: 100%; height: auto; border: none; overflow: hidden;",
                        srcdoc: iframeSrcdoc,
                        title: "Detailed Answer",
                        // Ensure the iframe is sandboxed for security, adjust the sandbox attributes as necessary for your use case
                        //sandbox: "allow-same-origin allow-scripts",
                    });

                    // Append an event listener to adjust the iframe's height based on its content after it loads
                    iframe.on("load", function () {
                        this.style.height = this.contentWindow.document.documentElement.scrollHeight + "px";
                    });

                    // Create a table cell and append the iframe to it, then append the cell to the row
                    const td = $("<td></td>").append(iframe);
                    tr.append(td);
                } else {
                    // If no long answers, append an empty cell
                    tr.append(`<td></td>`);
                }

                // Append short answers as is
                if (row["short_answers"].trim()) {
                    tr.append(`<td>${row["short_answers"]}</td>`);
                } else {
                    // If no short answers, append an empty cell
                    tr.append("<td></td>");
                }

                // Append the constructed row to the table body
                tableBody.append(tr);
            });

            resolve(); // Resolve the promise once all rows have been appended
        });
    }

    function updatePagination(currentPage, totalPages) {
        //console.log("pagination construction started");
        const paginationContainer = $(".pagination");
        paginationContainer.empty(); // Clear existing pagination buttons

        // Add 'First' button
        paginationContainer.append(
            `<li class="page-item ${currentPage === 1 ? "disabled" : ""}"><a class="page-link" href="#" data-page="1">First</a></li>`,
        );

        // Add 'Previous' button
        paginationContainer.append(
            `<li class="page-item ${currentPage === 1 ? "disabled" : ""}"><a class="page-link" href="#" data-page="${currentPage - 1}">Previous</a></li>`,
        );

        // Determine page numbers to display
        let startPage = Math.max(currentPage - 2, 1);
        let endPage = startPage + 4; // Display 5 pages at most
        if (endPage > totalPages) {
            endPage = totalPages;
            startPage = Math.max(endPage - 4, 1);
        }

        // Add page number buttons
        for (let i = startPage; i <= endPage; i++) {
            paginationContainer.append(
                `<li class="page-item ${i === currentPage ? "active" : ""}"><a class="page-link" href="#" data-page="${i}">${i}</a></li>`,
            );
        }

        // Add 'Next' button
        paginationContainer.append(
            `<li class="page-item ${currentPage === totalPages ? "disabled" : ""}"><a class="page-link" href="#" data-page="${currentPage + 1}">Next</a></li>`,
        );

        // Add 'Last' button
        paginationContainer.append(
            `<li class="page-item ${currentPage === totalPages ? "disabled" : ""}"><a class="page-link" href="#" data-page="${totalPages}">Last</a></li>`,
        );
    }

    function showLoadingIndicator() {
        $("#table-overlay").show(); // Show the table overlay
        $("#loading-indicator").show(); // Show the progress bar
        simulateProgressBar(); // Start simulating progress bar
    }

// Immediately set progress to 100% and then hide the progress bar
    const PROGRESS_LENGTH = 100;

    function completeProgressBar() {
        $("#loading-indicator .progress-bar")
            .css("width", "100%")
            .attr("aria-valuenow", PROGRESS_LENGTH);
        setTimeout(() => {
            // Optional delay to ensure users see the progress bar reaching 100%
            hideLoadingIndicator(); // Hide the progress bar after reaching 100%
        }, PROGRESS_LENGTH); // Adjust this delay as needed
    }

// Hide and reset the progress bar
    function hideLoadingIndicator() {
        $("#table-overlay").hide(); // Hide the table overlay
        $("#loading-indicator").hide(); // Hide the progress bar
        $("#loading-indicator .progress-bar")
            .css("width", "0%")
            .attr("aria-valuenow", 0); // Reset progress bar
    }

    let progressInterval; // Declare the interval variable outside the function scope

    function simulateProgressBar() {
        clearInterval(progressInterval); // Clear any existing interval to avoid overlaps
        let progress = 0;
        progressInterval = setInterval(function () {
            progress += 10; // Increment progress
            if (progress <= PROGRESS_LENGTH) {
                $("#loading-indicator .progress-bar")
                    .css("width", progress + "%")
                    .attr("aria-valuenow", progress);
            } else {
                clearInterval(progressInterval); // Stop the interval when progress reaches 100%
            }
        }, PROGRESS_LENGTH); // Update every 100ms
    }
