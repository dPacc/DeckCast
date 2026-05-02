export const PLUGIN_NAME = "DeckCast";

export const DEFAULT_TRANSFER_PORT = 8420;

export const YOUTUBE_CATEGORIES: Record<string, string> = {
  "1": "Film & Animation",
  "2": "Autos & Vehicles",
  "10": "Music",
  "15": "Pets & Animals",
  "17": "Sports",
  "20": "Gaming",
  "22": "People & Blogs",
  "23": "Comedy",
  "24": "Entertainment",
  "25": "News & Politics",
  "26": "Howto & Style",
  "27": "Education",
  "28": "Science & Technology",
};

export const PRIVACY_OPTIONS = [
  { label: "Public", value: "public" },
  { label: "Unlisted", value: "unlisted" },
  { label: "Private", value: "private" },
];

export const RESOLUTION_OPTIONS = [
  { label: "720p", value: "1280x720" },
  { label: "1080p", value: "1920x1080" },
  { label: "480p", value: "854x480" },
];

export const BITRATE_OPTIONS = [
  { label: "2500 kbps", value: "2500k" },
  { label: "4000 kbps", value: "4000k" },
  { label: "6000 kbps", value: "6000k" },
  { label: "8000 kbps", value: "8000k" },
];

export const FRAMERATE_OPTIONS = [
  { label: "24 fps", value: 24 },
  { label: "30 fps", value: 30 },
  { label: "60 fps", value: 60 },
];
