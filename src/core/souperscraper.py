from typing import Optional, Union, Literal, Type, Iterable, Callable
from functools import partial, wraps
from pathlib import Path
from time import sleep

from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.key_input import KeyInput
from selenium.webdriver.common.actions.wheel_input import WheelInput
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
    WebDriverException,
    TimeoutException,
)

WebDriverType = Literal["chrome", "edge", "firefox", "ie", "safari", "webkitgtk", "wpewebkit"]
SoupParser = Literal["html.parser", "lxml", "lxml-xml", "xml", "html5lib"]


def import_webdriver(
    webdriver_type: WebDriverType,
) -> tuple[Type, Type, Optional[Type]]:
    """Imports and returns Selenium WebDriver class, Service class, and Options class for webdriver_type"""

    webdriver_modules = {
        "chrome": {
            "Service": "selenium.webdriver.chrome.service",
            "Options": "selenium.webdriver.chrome.options",
            "WebDriver": "selenium.webdriver.chrome.webdriver",
        },
        "edge": {
            "Service": "selenium.webdriver.edge.service",
            "Options": "selenium.webdriver.edge.options",
            "WebDriver": "selenium.webdriver.edge.webdriver",
        },
        "firefox": {
            "Service": "selenium.webdriver.firefox.service",
            "Options": "selenium.webdriver.firefox.options",
            "WebDriver": "selenium.webdriver.firefox.webdriver",
        },
        "ie": {
            "Service": "selenium.webdriver.ie.service",
            "Options": "selenium.webdriver.ie.options",
            "WebDriver": "selenium.webdriver.ie.webdriver",
        },
        "safari": {
            "Service": "selenium.webdriver.safari.service",
            "WebDriver": "selenium.webdriver.safari.webdriver",
        },
        "webkitgtk": {
            "Service": "selenium.webdriver.webkitgtk.service",
            "Options": "selenium.webdriver.webkitgtk.options",
            "WebDriver": "selenium.webdriver.webkitgtk.webdriver",
        },
        "wpewebkit": {
            "Service": "selenium.webdriver.wpewebkit.service",
            "Options": "selenium.webdriver.wpewebkit.options",
            "WebDriver": "selenium.webdriver.wpewebkit.webdriver",
        },
    }

    if webdriver_type in webdriver_modules:
        module = webdriver_modules[webdriver_type]
        from importlib import import_module

        return (
            import_module(module["WebDriver"]).WebDriver,
            import_module(module["Service"]).Service,
            import_module(module["Options"]).Options if "Options" in module else None,
        )
    else:
        raise ValueError(f"Unsupported webdriver type: {webdriver_type}")


class SouperScraper:
    def __init__(
        self,
        soup_parser: SoupParser = "html.parser",
        executable_path: Union[str, Path] = "./chromedriver",
        selenium_webdriver_type: WebDriverType = "chrome",
        selenium_service_kwargs: Optional[dict] = None,
        selenium_options_args: Optional[Iterable[str]] = None,
        selenium_webdriver_cls_override: Optional[Type] = None,
        selenium_service_cls_override: Optional[Type] = None,
        selenium_options_cls_override: Optional[Type] = None,
        keep_alive: bool = True,
        user_agent: Optional[str] = None,
        proxy: Optional[str] = None,
        save_dynamic_methods: bool = True,
    ) -> None:
        # Check if executable_path exists and add it to the Selenium Service kwargs
        executable_path = Path(executable_path) if isinstance(executable_path, str) else executable_path
        if not executable_path.exists():
            raise FileNotFoundError(
                f"Executable path {executable_path} does not exist. Use souperscraper.get_chromedriver() to download chromedriver."
            )

        selenium_service_kwargs = selenium_service_kwargs or {}
        if executable_path and "executable_path" not in selenium_service_kwargs:
            selenium_service_kwargs["executable_path"] = str(executable_path)

        # Import Selenium WebDriver class, Service class, and Options class for webdriver_type or use the override classes
        (
            selenium_webdriver_cls,
            selenium_service_cls,
            selenium_options_cls,
        ) = import_webdriver(selenium_webdriver_type)
        selenium_webdriver_cls = selenium_webdriver_cls_override or selenium_webdriver_cls
        selenium_service_cls = selenium_service_cls_override or selenium_service_cls
        selenium_options_cls = selenium_options_cls_override or selenium_options_cls

        # Init Selenium Service and Options objects
        self.selenium_service = selenium_service_cls(**selenium_service_kwargs)
        self.selenium_options = selenium_options_cls() if selenium_options_cls else None

        # Add arguments to Selenium Options object
        if self.selenium_options:
            # Add args passed to SouperScraper constructor
            if selenium_options_args:
                for arg in selenium_options_args:
                    self.selenium_options.add_argument(arg)

            # Add user_agent to Selenium Options object
            if user_agent:
                self.selenium_options.add_argument(f'--user-agent="{user_agent}"')

            # Add proxy to Selenium Options object
            if proxy:
                self.selenium_options.add_argument(f'--proxy-server="{proxy}"')

        # Create Selenium WebDriver object from Service and Options objects
        self.webdriver = selenium_webdriver_cls(
            service=self.selenium_service,
            options=self.selenium_options,
            keep_alive=keep_alive,
        )

        # Save for later to use when calling SoupScraper.soup
        self.soup_parser = soup_parser
        self.user_agent = user_agent
        self.proxy = proxy

        # Save dynamic methods for later use
        self.save_dynamic_methods = save_dynamic_methods

    def __del__(self):
        """Quit webdriver when SoupScraper object is deleted or garbage collected"""
        if hasattr(self, "webdriver"):
            self.webdriver.quit()

    def __getattr__(self, attr):
        # Check if attribute already exists in SoupScraper object
        # (Defined in this class or dynamically created by __getattr__ with save_dynamic_methods=True)
        if attr in dir(self):
            return super().__getattribute__(attr)

        # Check if attribute exists in webdriver object
        if (webdriver := super().__getattribute__("webdriver")) and attr in dir(webdriver):
            return getattr(webdriver, attr)

        # If the attr starts with soup, return the attribute from self.soup
        if attr.startswith("soup_"):
            return getattr(super().__getattribute__("soup"), attr[5:])

        # Try to create a dynamic attr not found in the SoupScraper, WebDriver, or BeautifulSoup objects
        dynamic_method = None

        # Check if attr is a try_ wrapped method or attempt to find locator and expected_condition
        if attr.startswith("try_"):
            dynamic_method = super().__getattribute__("_try_wrapper")(getattr(self, attr[4:]))
        else:
            # Split attribute by '_' to check for 'soup', 'by', 'wait', etc.
            split_attr = attr.split("_")

            # Attempt to find locator and expected_condition in split_attr
            # If found, return a partial function with locator and expected_condition
            # For example:
            # self.wait_for_visibility_of_element_located_by_id(locator_value) is equivalent to
            # WebDriverWait(self.webdriver, 3).until(EC.visibility_of_element_located((By.ID, locator_value))
            locator = None
            expected_condition = None
            if "by" in split_attr:
                by_index = split_attr.index("by")
                locator = " ".join(split_attr[by_index + 1 :])
                split_attr = split_attr[:by_index]

            if "wait" in split_attr:
                wait_index = split_attr.index("wait")
                offset = 3 if "not" in split_attr else 2
                expected_condition = getattr(EC, "_".join(split_attr[wait_index + offset :]))
                split_attr = split_attr[: wait_index + offset]

            bare_attr = "_".join(split_attr)  # attr after removing locator and expected_condition
            if locator and expected_condition:
                dynamic_method = partial(getattr(self, bare_attr), expected_condition, locator)
            elif locator:
                dynamic_method = partial(getattr(self, bare_attr), locator)
            elif expected_condition:
                dynamic_method = partial(getattr(self, bare_attr), expected_condition)

        if dynamic_method:
            # Save dynamic method if save_dynamic_methods is True
            if self.save_dynamic_methods:
                setattr(self, attr, dynamic_method)
            return dynamic_method

        # Call super().__getattr__ if dynamic method is not found
        return super().__getattribute__(attr)

    def _try_wrapper(self, func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, ignore_exceptions=(WebDriverException,), **kwargs):
            try:
                return func(self, *args, **kwargs)
            except ignore_exceptions as e:
                print(e)
                return None

        return wrapper

    def _get_soup(self) -> BeautifulSoup:
        """
        Returns BeautifulSoup object from webdriver.page_source.
        Default parser is 'html.parser'.
        """
        return BeautifulSoup(self.webdriver.page_source, self.soup_parser)

    def _get_current_url(self) -> str:
        """Returns webdriver.current_url"""
        return self.webdriver.current_url

    def _get_current_title(self) -> str:
        """Returns webdriver.title"""
        return self.webdriver.title

    def _get_current_window_handle(self) -> str:
        """Returns webdriver.current_window_handle"""
        return self.webdriver.current_window_handle

    def _get_all_window_handles(self) -> list[str]:
        """Returns webdriver.window_handles"""
        return self.webdriver.window_handles

    def _new_window_handle(self, window_type="window", url=None, sleep_secs=None) -> None:
        self.webdriver.switch_to.new_window(window_type)
        if url:
            self.goto(url, sleep_secs)

    def _switch_to_window_handle(self, window_handle) -> None:
        """Switch to window with webdriver.switch_to.window(window_handle)"""
        self.webdriver.switch_to.window(window_handle)

    def _close_window(self, window_handle=None, switch_to_window_handle=None) -> None:
        """Close window with webdriver.close()"""
        if window_handle:
            self._switch_to_window_handle(window_handle)
        self.webdriver.close()
        if switch_to_window_handle:
            self._switch_to_window_handle(switch_to_window_handle)

    def _get_window_handle_by_index(self, index) -> Optional[str]:
        """Returns window handle by index from webdriver.window_handles"""
        try:
            return self.webdriver.window_handles[index]
        except IndexError:
            return None

    def _get_window_handle_by_title(self, title) -> Optional[str]:
        """Returns window handle by title from webdriver.window_handles"""
        for window_handle in self._get_all_window_handles():
            self._switch_to_window_handle(window_handle)
            if self.current_title == title:
                return window_handle
        return None

    def _get_window_handle_by_url(self, url) -> Optional[str]:
        """Returns window handle by url from webdriver.window_handles"""
        for window_handle in self._get_all_window_handles():
            self._switch_to_window_handle(window_handle)
            if self.current_url == url:
                return window_handle
        return None

    def switch_to_window(self, index=None, title=None, url=None, window_handle=None) -> Optional[str]:
        if index:
            window_handle = self._get_window_handle_by_index(index)
        elif title:
            window_handle = self._get_window_handle_by_title(title)
        elif url:
            window_handle = self._get_window_handle_by_url(url)

        if window_handle:
            self._switch_to_window_handle(window_handle)
        return window_handle

    def switch_to_tab(self, index=None, title=None, url=None, window_handle=None) -> Optional[str]:
        return self.switch_to_window(index, title, url, window_handle)

    def new_tab(self, url=None, sleep_secs=None) -> str:
        self._new_window_handle("tab", url, sleep_secs)
        return self._get_all_window_handles()[-1]

    def new_window(self, url=None, sleep_secs=None) -> str:
        self._new_window_handle("window", url, sleep_secs)
        return self._get_all_window_handles()[-1]

    def goto(self, url, sleep_secs=None) -> str:
        """Goto url with webdriver.get(url)"""
        self.webdriver.get(url)
        if sleep_secs and sleep_secs > 0:
            sleep(sleep_secs)

        return self.webdriver.current_url

    @property
    def soup(self) -> BeautifulSoup:
        """Returns BeautifulSoup object from webdriver.page_source"""
        return self._get_soup()

    @property
    def current_url(self) -> str:
        """Returns webdriver.current_url"""
        return self._get_current_url()

    @property
    def current_title(self) -> str:
        """Returns webdriver.title"""
        return self._get_current_title()

    @property
    def current_window_handle(self) -> str:
        """Returns webdriver.current_window_handle"""
        return self._get_current_window_handle()

    @property
    def current_tab(self) -> str:
        """Returns webdriver.current_window_handle"""
        return self._get_current_window_handle()

    @property
    def current_window(self) -> str:
        """Returns webdriver.current_window_handle"""
        return self._get_current_window_handle()

    @property
    def all_window_handles(self) -> list[str]:
        """Returns webdriver.window_handles"""
        return self._get_all_window_handles()

    @property
    def tabs(self) -> list[str]:
        """Returns webdriver.window_handles"""
        return self._get_all_window_handles()

    @property
    def windows(self) -> list[str]:
        """Returns webdriver.window_handles"""
        return self._get_all_window_handles()

    # GET WRAPPED WEBDRIVER METHODS (ActionChains, ActionBuilder, Alert, WebDriverWait)

    def get_action_chains(self, duration: int = 250, devices: Optional[list] = None) -> ActionChains:
        """Returns ActionChains object from self.webdriver with duration and devices"""
        return ActionChains(self.webdriver, duration, devices)

    def get_action_builder(
        self,
        mouse: Optional[PointerInput] = None,
        wheel: Optional[WheelInput] = None,
        keyboard: Optional[KeyInput] = None,
        duration: int = 250,
    ) -> ActionBuilder:
        """Returns ActionBuilder object from self.webdriver with mouse, wheel, keyboard, and duration"""
        return ActionBuilder(self.webdriver, mouse, wheel, keyboard, duration)

    def get_alert(self) -> Alert:
        """Returns Alert object from self.webdriver"""
        return Alert(self.webdriver)

    def get_wait(self, timeout, poll_frequency, ignored_exceptions) -> WebDriverWait:
        """Returns WebDriverWait object from self.webdriver with timeout, poll_frequency, and ignored_exceptions"""
        return WebDriverWait(self.webdriver, timeout, poll_frequency, ignored_exceptions)

    def _wait(
        self,
        method,
        *method_args,
        timeout=3.0,
        poll_frequency=0.5,
        ignored_exceptions=None,
        until=True,
    ) -> Union[WebElement, bool, None]:
        """Wait for method(*method_args) with WebDriverWait"""

        wait = self.get_wait(timeout, poll_frequency, ignored_exceptions)
        try:
            if until:
                return wait.until(method(method_args)) if len(method_args) > 1 else wait.until(method(*method_args))
            else:
                return (
                    wait.until_not(method(method_args))
                    if len(method_args) > 1
                    else wait.until_not(method(*method_args))
                )
        except TimeoutException as e:
            print(e)
            return None

    # WAIT FOR ELEMENT METHODS -> element(s)

    def wait_until(
        self,
        expected_condition: Callable,
        *expected_condition_args,
        timeout=3.0,
        poll_frequency=0.5,
        ignored_exceptions=None,
    ):
        """Wait for element with expected_condition(locator, locator_value) or return None if timeout"""
        return self._wait(
            expected_condition,
            *expected_condition_args,
            timeout=timeout,
            poll_frequency=poll_frequency,
            ignored_exceptions=ignored_exceptions,
        )

    def wait_until_not(
        self,
        expected_condition: Callable,
        *expected_condition_args,
        timeout=3.0,
        poll_frequency=0.5,
        ignored_exceptions=None,
    ):
        """Wait for element with expected_condition(locator, locator_value) or return None if timeout"""
        return self._wait(
            expected_condition,
            *expected_condition_args,
            timeout=timeout,
            poll_frequency=poll_frequency,
            ignored_exceptions=ignored_exceptions,
            until=False,
        )

    def wait_for(
        self,
        expected_condition: Callable,
        *expected_condition_args,
        timeout=3.0,
        poll_frequency=0.5,
        ignored_exceptions=None,
    ):
        """Wait for element with expected_condition(locator, locator_value) or return None if timeout"""
        return self._wait(
            expected_condition,
            *expected_condition_args,
            timeout=timeout,
            poll_frequency=poll_frequency,
            ignored_exceptions=ignored_exceptions,
        )

    def wait_for_not(
        self,
        expected_condition: Callable,
        *expected_condition_args,
        timeout=3.0,
        poll_frequency=0.5,
        ignored_exceptions=None,
    ):
        """Wait for element with expected_condition(locator, locator_value) or return None if timeout"""
        return self._wait(
            expected_condition,
            *expected_condition_args,
            timeout=timeout,
            poll_frequency=poll_frequency,
            ignored_exceptions=ignored_exceptions,
            until=False,
        )

    # SCROLL TO ELEMENT METHODS

    def scroll_to(self, element: WebElement) -> WebElement:
        """Scroll to element with element.location_once_scrolled_into_view"""
        self.webdriver.execute_script("arguments[0].scrollIntoView(true);", element)
        return element

    def scroll_to_element(self, locator: str, locator_value: str) -> WebElement:
        """Scroll to element with locator and locator_value"""
        element = self.find_element(locator, locator_value)
        self.scroll_to(element)
        return element

    # BY TEXT SHORTCUTS

    def find_element_by_text(self, text: str) -> WebElement:
        """Find element by text with xpath"""
        return self.find_element_by_xpath(f"//*[text()='{text}']")

    def find_elements_by_text(self, text: str) -> WebElement:
        """Find elements by text with xpath"""
        return self.find_elements_by_xpath(f"//*[text()='{text}']")

    def wait_for_element_by_text(
        self, text: str, timeout=3.0, poll_frequency=0.5, ignored_exceptions=None
    ) -> WebElement:
        """Wait for element by text with xpath"""
        return self.wait_for_presence_of_element_located_by_xpath(
            f"//*[text()='{text}']",
            timeout=timeout,
            poll_frequency=poll_frequency,
            ignored_exceptions=ignored_exceptions,
        )

    def scroll_to_element_by_text(self, text: str) -> WebElement:
        """Scroll to element by text with xpath"""
        element = self.find_element_by_text(text)
        self.scroll_to(element)
        return element
