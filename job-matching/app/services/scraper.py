from typing import List, Dict, Any, Optional
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
from loguru import logger
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from app.config.settings import settings
from app.schemas.job import JobCreate, CompanyInfo

class ScraperService:
    def __init__(self):
        """Initialize scraper service"""
        self.session = None
        self.driver = None
        self.headers = {
            "User-Agent": settings.USER_AGENT
        }
        self._setup_selenium()

    def _setup_selenium(self):
        """Set up Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(
                executable_path=settings.CHROME_DRIVER_PATH,
                options=chrome_options
            )
        except Exception as e:
            logger.error(f"Error setting up Selenium: {str(e)}")
            raise

    async def init_session(self):
        """Initialize aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)

    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
        if self.driver:
            self.driver.quit()

    async def scrape_jobs(
        self,
        job_title: str,
        location: str,
        job_boards: Optional[List[str]] = None
    ) -> List[JobCreate]:
        """Scrape jobs from multiple job boards"""
        if not job_boards:
            job_boards = settings.SUPPORTED_JOB_BOARDS

        await self.init_session()
        jobs = []
        tasks = []

        for board in job_boards:
            if board == "linkedin":
                tasks.append(self.scrape_linkedin(job_title, location))
            elif board == "indeed":
                tasks.append(self.scrape_indeed(job_title, location))
            elif board == "glassdoor":
                tasks.append(self.scrape_glassdoor(job_title, location))

        # Run scraping tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and filter results
        for board_jobs in results:
            if isinstance(board_jobs, list):
                jobs.extend(board_jobs)
            else:
                logger.error(f"Error scraping jobs: {str(board_jobs)}")

        return jobs

    async def scrape_linkedin(
        self,
        job_title: str,
        location: str
    ) -> List[JobCreate]:
        """Scrape jobs from LinkedIn"""
        try:
            jobs = []
            page = 1
            total_jobs = 0

            while len(jobs) < settings.MAX_JOBS_PER_QUERY:
                # Construct search URL
                url = (
                    f"https://www.linkedin.com/jobs/search?"
                    f"keywords={job_title}&location={location}"
                    f"&start={25 * (page - 1)}"
                )

                # Use Selenium for dynamic content
                self.driver.get(url)
                await asyncio.sleep(settings.SEARCH_DELAY)

                # Wait for job cards to load
                WebDriverWait(self.driver, settings.SCRAPE_TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "job-card-container"))
                )

                # Parse job listings
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                job_cards = soup.find_all("div", class_="job-card-container")

                if not job_cards:
                    break

                for card in job_cards:
                    try:
                        # Extract job details
                        job_link = card.find("a", class_="job-card-list__title")
                        company_elem = card.find("a", class_="job-card-container__company-name")

                        if not job_link or not company_elem:
                            continue

                        job_url = job_link.get("href")
                        
                        # Get detailed job info
                        job_details = await self._get_linkedin_job_details(job_url)
                        if job_details:
                            jobs.append(job_details)
                            total_jobs += 1

                        if total_jobs >= settings.MAX_JOBS_PER_QUERY:
                            break

                    except Exception as e:
                        logger.error(f"Error parsing LinkedIn job card: {str(e)}")
                        continue

                page += 1

            return jobs

        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {str(e)}")
            return []

    async def _get_linkedin_job_details(self, job_url: str) -> Optional[JobCreate]:
        """Get detailed job information from LinkedIn job page"""
        try:
            # Use Selenium to load job details page
            self.driver.get(job_url)
            await asyncio.sleep(settings.SEARCH_DELAY)

            # Wait for content to load
            WebDriverWait(self.driver, settings.SCRAPE_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job-view-layout"))
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Extract job information
            title = soup.find("h1", class_="job-title").text.strip()
            company = soup.find("a", class_="company-name").text.strip()
            location = soup.find("span", class_="location").text.strip()
            
            description_elem = soup.find("div", class_="description__text")
            description = description_elem.text.strip() if description_elem else ""

            # Extract company information
            company_info = CompanyInfo(
                name=company,
                industry=self._safe_extract(soup, "span", "company-industry"),
                size=self._safe_extract(soup, "span", "company-size"),
                website=self._safe_extract(soup, "a", "company-website", attr="href")
            )

            # Create job object
            return JobCreate(
                title=title,
                company=company,
                location=location,
                description=description,
                source="linkedin",
                source_url=job_url,
                company_info=company_info,
                posted_at=datetime.utcnow()  # LinkedIn doesn't always show exact date
            )

        except Exception as e:
            logger.error(f"Error getting LinkedIn job details: {str(e)}")
            return None

    async def scrape_indeed(
        self,
        job_title: str,
        location: str
    ) -> List[JobCreate]:
        """Scrape jobs from Indeed"""
        try:
            jobs = []
            page = 0

            while len(jobs) < settings.MAX_JOBS_PER_QUERY:
                # Construct search URL
                url = (
                    f"https://www.indeed.com/jobs?"
                    f"q={job_title}&l={location}"
                    f"&start={10 * page}"
                )

                async with self.session.get(url) as response:
                    if response.status != 200:
                        break

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")
                    job_cards = soup.find_all("div", class_="job_seen_beacon")

                    if not job_cards:
                        break

                    for card in job_cards:
                        try:
                            # Extract job details
                            title_elem = card.find("h2", class_="jobTitle")
                            company_elem = card.find("span", class_="companyName")
                            
                            if not title_elem or not company_elem:
                                continue

                            job_url = "https://www.indeed.com" + title_elem.find("a")["href"]
                            
                            # Get detailed job info
                            job_details = await self._get_indeed_job_details(job_url)
                            if job_details:
                                jobs.append(job_details)

                            if len(jobs) >= settings.MAX_JOBS_PER_QUERY:
                                break

                            # Respect rate limits
                            await asyncio.sleep(settings.SEARCH_DELAY)

                        except Exception as e:
                            logger.error(f"Error parsing Indeed job card: {str(e)}")
                            continue

                page += 1

            return jobs

        except Exception as e:
            logger.error(f"Error scraping Indeed: {str(e)}")
            return []

    async def _get_indeed_job_details(self, job_url: str) -> Optional[JobCreate]:
        """Get detailed job information from Indeed job page"""
        try:
            async with self.session.get(job_url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                # Extract job information
                title = soup.find("h1", class_="jobsearch-JobInfoHeader-title").text.strip()
                company = soup.find("div", class_="jobsearch-CompanyInfoContainer").text.strip()
                location = soup.find("div", class_="jobsearch-JobInfoHeader-subtitle").text.strip()
                
                description_elem = soup.find("div", id="jobDescriptionText")
                description = description_elem.text.strip() if description_elem else ""

                # Extract company information
                company_info = CompanyInfo(
                    name=company,
                    industry=self._safe_extract(soup, "div", "company-industry"),
                    size=self._safe_extract(soup, "div", "company-size")
                )

                # Try to extract posting date
                date_elem = soup.find("span", class_="jobsearch-JobMetadataFooter-item")
                posted_at = self._parse_date(date_elem.text if date_elem else "")

                return JobCreate(
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    source="indeed",
                    source_url=job_url,
                    company_info=company_info,
                    posted_at=posted_at or datetime.utcnow()
                )

        except Exception as e:
            logger.error(f"Error getting Indeed job details: {str(e)}")
            return None

    async def scrape_glassdoor(
        self,
        job_title: str,
        location: str
    ) -> List[JobCreate]:
        """Scrape jobs from Glassdoor"""
        try:
            jobs = []
            page = 1

            while len(jobs) < settings.MAX_JOBS_PER_QUERY:
                # Construct search URL
                url = (
                    f"https://www.glassdoor.com/Job/jobs.htm?"
                    f"sc.keyword={job_title}&locT=C&locId={location}"
                    f"&p={page}"
                )

                # Use Selenium for Glassdoor's dynamic content
                self.driver.get(url)
                await asyncio.sleep(settings.SEARCH_DELAY)

                # Wait for job cards to load
                WebDriverWait(self.driver, settings.SCRAPE_TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "react-job-listing"))
                )

                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                job_cards = soup.find_all("div", class_="react-job-listing")

                if not job_cards:
                    break

                for card in job_cards:
                    try:
                        # Extract job details
                        title_elem = card.find("a", class_="jobLink")
                        if not title_elem:
                            continue

                        job_url = "https://www.glassdoor.com" + title_elem["href"]
                        
                        # Get detailed job info
                        job_details = await self._get_glassdoor_job_details(job_url)
                        if job_details:
                            jobs.append(job_details)

                        if len(jobs) >= settings.MAX_JOBS_PER_QUERY:
                            break

                    except Exception as e:
                        logger.error(f"Error parsing Glassdoor job card: {str(e)}")
                        continue

                page += 1

            return jobs

        except Exception as e:
            logger.error(f"Error scraping Glassdoor: {str(e)}")
            return []

    async def _get_glassdoor_job_details(self, job_url: str) -> Optional[JobCreate]:
        """Get detailed job information from Glassdoor job page"""
        try:
            # Use Selenium for dynamic content
            self.driver.get(job_url)
            await asyncio.sleep(settings.SEARCH_DELAY)

            # Wait for content to load
            WebDriverWait(self.driver, settings.SCRAPE_TIMEOUT).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job-description"))
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Extract job information
            title = self._safe_extract(soup, "div", "job-title")
            company = self._safe_extract(soup, "div", "employer-name")
            location = self._safe_extract(soup, "div", "location")
            
            description_elem = soup.find("div", class_="job-description")
            description = description_elem.text.strip() if description_elem else ""

            # Extract company information
            company_info = CompanyInfo(
                name=company,
                industry=self._safe_extract(soup, "div", "company-industry"),
                size=self._safe_extract(soup, "div", "company-size"),
                website=self._safe_extract(soup, "a", "company-website", attr="href")
            )

            # Extract posting date
            date_elem = soup.find("div", class_="job-posting-date")
            posted_at = self._parse_date(date_elem.text if date_elem else "")

            return JobCreate(
                title=title,
                company=company,
                location=location,
                description=description,
                source="glassdoor",
                source_url=job_url,
                company_info=company_info,
                posted_at=posted_at or datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error getting Glassdoor job details: {str(e)}")
            return None

    def _safe_extract(
        self,
        soup: BeautifulSoup,
        tag: str,
        class_name: str,
        attr: Optional[str] = None
    ) -> str:
        """Safely extract text or attribute from BeautifulSoup element"""
        try:
            element = soup.find(tag, class_=class_name)
            if element:
                return element[attr] if attr else element.text.strip()
            return ""
        except:
            return ""

    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """Parse various date formats to datetime"""
        try:
            date_text = date_text.lower().strip()
            now = datetime.utcnow()

            if "just posted" in date_text or "today" in date_text:
                return now
            elif "yesterday" in date_text:
                return now - timedelta(days=1)
            elif "days ago" in date_text:
                days = int(date_text.split()[0])
                return now - timedelta(days=days)
            elif "weeks ago" in date_text:
                weeks = int(date_text.split()[0])
                return now - timedelta(weeks=weeks)
            elif "months ago" in date_text:
                months = int(date_text.split()[0])
                return now - timedelta(days=30*months)
            
            return None
        except:
            return None

    async def validate_job(self, job: JobCreate) -> bool:
        """Validate scraped job data"""
        required_fields = ["title", "company", "description", "location"]
        return all(bool(getattr(job, field, None)) for field in required_fields)
