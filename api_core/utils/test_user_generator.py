"""
Test User Data Generator

Generates realistic random test data for user registration E2E flows.
Includes: phone numbers, names, dates of birth, cities and coordinates.

The generated payload is an example shape. Replace generate_user() with
whatever your own registration endpoint accepts.
"""

import random
from datetime import datetime, timedelta


class TestUserGenerator:
    """
    Generates random test user data for E2E testing.

    Usage:
        generator = TestUserGenerator()
        user_data = generator.generate_user()
    """

    # First-name pool
    # Placeholder names, deliberately. This generates synthetic test users, so
    # it needs name-shaped strings; the pools were previously common real
    # first names, which identify nobody but read exactly like real user data.
    # Alice and Bob do not.
    MALE_NAMES = [
        "Alan", "Bob", "Carl", "Dave", "Erik", "Frank", "Gus", "Hugo",
        "Ivan", "Jack", "Karl", "Leon", "Marco", "Nils", "Omar", "Paul"
    ]

    FEMALE_NAMES = [
        "Alice", "Beth", "Carol", "Dana", "Erin", "Fiona", "Grace", "Heidi",
        "Iris", "Judy", "Kira", "Lena", "Mara", "Nina", "Olive", "Peggy"
    ]

    # Indian last names
    LAST_NAMES = [
        "Archer", "Baker", "Carter", "Draper", "Ellis", "Fisher", "Gardner",
        "Harper", "Ingram", "Jenkins", "Keller", "Lawson", "Mercer", "Norton"
    ]

    # Indian cities with approximate coordinates
    CITIES = [
        {"name": "Mumbai, Maharashtra", "lat": 19.0760, "lon": 72.8777},
        {"name": "Delhi, Delhi", "lat": 28.7041, "lon": 77.1025},
        {"name": "Bangalore, Karnataka", "lat": 12.9716, "lon": 77.5946},
        {"name": "Hyderabad, Telangana", "lat": 17.3850, "lon": 78.4867},
        {"name": "Chennai, Tamil Nadu", "lat": 13.0827, "lon": 80.2707},
        {"name": "Kolkata, West Bengal", "lat": 22.5726, "lon": 88.3639},
        {"name": "Pune, Maharashtra", "lat": 18.5204, "lon": 73.8567},
        {"name": "Ahmedabad, Gujarat", "lat": 23.0225, "lon": 72.5714},
        {"name": "Jaipur, Rajasthan", "lat": 26.9124, "lon": 75.7873},
        {"name": "Lucknow, Uttar Pradesh", "lat": 26.8467, "lon": 80.9462},
        {"name": "Chandigarh, Chandigarh", "lat": 30.7333, "lon": 76.7794},
        {"name": "Indore, Madhya Pradesh", "lat": 22.7196, "lon": 75.8577},
        {"name": "Kochi, Kerala", "lat": 9.9312, "lon": 76.2673},
        {"name": "Bhopal, Madhya Pradesh", "lat": 23.2599, "lon": 77.4126},
        {"name": "Patna, Bihar", "lat": 25.5941, "lon": 85.1376},
        {"name": "Surat, Gujarat", "lat": 21.1702, "lon": 72.8311},
        {"name": "Nagpur, Maharashtra", "lat": 21.1458, "lon": 79.0882},
        {"name": "Visakhapatnam, Andhra Pradesh", "lat": 17.6868, "lon": 83.2185},
        {"name": "Gurgaon, Haryana", "lat": 28.4595, "lon": 77.0266},
        {"name": "Noida, Uttar Pradesh", "lat": 28.5355, "lon": 77.3910}
    ]

    def __init__(self, seed: int = None):
        """
        Initialize generator with optional seed for reproducibility.

        Args:
            seed: Random seed (optional)
        """
        if seed:
            random.seed(seed)

    def generate_phone_number(self, used_numbers: list[str] = None) -> str:
        """
        Generate unique 10-digit Indian phone number.

        Args:
            used_numbers: List of already used numbers to avoid duplicates

        Returns:
            10-digit phone number as string
        """
        used_numbers = used_numbers or []

        while True:
            # Generate 10-digit number starting with 5-9
            first_digit = random.randint(5, 9)
            remaining = ''.join([str(random.randint(0, 9)) for _ in range(9)])
            phone = f"{first_digit}{remaining}"

            if phone not in used_numbers:
                return phone

    def generate_name(self, gender: str = None) -> str:
        """
        Generate random Indian name.

        Args:
            gender: "Male" or "Female" (randomly chosen if not specified)

        Returns:
            Full name (first + last)
        """
        if not gender:
            gender = random.choice(["Male", "Female"])

        if gender == "Male":
            first_name = random.choice(self.MALE_NAMES)
        else:
            first_name = random.choice(self.FEMALE_NAMES)

        last_name = random.choice(self.LAST_NAMES)
        return f"{first_name} {last_name}"

    def generate_dob(self, min_age: int = 18, max_age: int = 65) -> str:
        """
        Generate random date of birth.

        Args:
            min_age: Minimum age in years
            max_age: Maximum age in years

        Returns:
            Date in YYYY-MM-DD format
        """
        today = datetime.now()
        min_date = today - timedelta(days=max_age * 365)
        max_date = today - timedelta(days=min_age * 365)

        random_date = min_date + timedelta(
            days=random.randint(0, (max_date - min_date).days)
        )

        return random_date.strftime("%Y-%m-%d")

    def generate_city_with_coords(self) -> tuple[str, float, float]:
        """
        Generate a random city with coordinates.

        Returns:
            Tuple of (place_name, latitude, longitude)
        """
        city = random.choice(self.CITIES)

        # Add small random variation to coordinates (within ~10km)
        lat_variation = random.uniform(-0.05, 0.05)
        lon_variation = random.uniform(-0.05, 0.05)

        lat = round(city["lat"] + lat_variation, 5)
        lon = round(city["lon"] + lon_variation, 5)

        return city["name"], lat, lon

    def generate_user(self, phone_number: str = None) -> dict:
        """
        Generate complete user data for registration.

        Args:
            phone_number: Optional phone number (generated if not provided)

        Returns:
            Dictionary with user data
        """
        gender = random.choice(["Male", "Female"])
        city, lat, lon = self.generate_city_with_coords()

        return {
            "phoneNumber": phone_number or self.generate_phone_number(),
            "name": self.generate_name(gender),
            "gender": gender,
            "dob": self.generate_dob(),
            "city": city,
            "latitude": str(lat),
            "longitude": str(lon),
            "country": "IN",
            "countryCode": "+91"
        }

    def generate_multiple_users(self, count: int) -> list[dict]:
        """
        Generate multiple unique users.

        Args:
            count: Number of users to generate

        Returns:
            List of user data dictionaries
        """
        users = []
        used_numbers = []

        for _ in range(count):
            phone = self.generate_phone_number(used_numbers)
            used_numbers.append(phone)
            user = self.generate_user(phone)
            users.append(user)

        return users


# Convenience function
def generate_test_users(count: int = 20, seed: int = None) -> list[dict]:
    """
    Quick function to generate test users.

    Args:
        count: Number of users to generate
        seed: Optional random seed

    Returns:
        List of user data dictionaries

    Example:
        users = generate_test_users(20)
        for user in users:
            print(user["phoneNumber"], user["name"])
    """
    generator = TestUserGenerator(seed)
    return generator.generate_multiple_users(count)
