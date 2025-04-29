# 4chanSimu

A lightweight, anonymous discussion forum inspired by 4chan, built with a Flask backend and a vanilla JavaScript frontend using HTML, CSS, and JS templates.

## Features

- **Anonymous Posting**: No user registration required; posters identify with a user ID.
- **Multiple Boards**: `/b/` (NSFW allowed) and `/pol/` (No NSFW).
- **Text Moderation**: Built-in toxic content detection via Hugging Face's `unitary/toxic-bert` model.
- **Image Uploads**: Users can attach images to posts; images are saved to the `uploads/` folder.
- **NSFW Placeholder**: OpenCLIP-based image feature extractor stub for future NSFW classification.
- **Admin Panel**: Secure login, view all posts (approved or pending), approve or delete posts.
- **Flask Templates**: `templates/index.html` and `templates/admin.html` served with `render_template`.
- **Static Assets**: CSS and JS assets in `static/` (including `styles.css`, `script.js`, `admin.js`).

## Table of Contents

- [Demo](#demo)
- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Notes](#notes)
- [Future Improvements](#future-improvements)
- [License](#license)

## Demo

_Coming soon!_

## Getting Started

Clone this repository and follow the installation steps below.

```bash
git clone https://github.com/TheSuper-Media3004/the4chan.git
cd the4chan
```

## Prerequisites

- Python 3.8+
- MySQL or SQLite (default SQLite if no `DATABASE_URL` provided)
- Node.js/npm (optional, if you plan to integrate a bundler in the future)

## Installation

1. **Backend Setup**:
   ```bash
   cd backend  # if you split into folders, otherwise project root
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   ```

2. **Database**:
   - Default: SQLite at `site.db`.
   - To use MySQL, set `DATABASE_URL` in `.env` (see [Configuration](#configuration)).

3. **Frontend & Assets**:
   - All HTML templates are in `templates/`.
   - Static CSS/JS in `static/`.
   - No build step required; files are served by Flask.

## Configuration

Create a `.env` file in the project root:

```dotenv
SECRET_KEY=your_flask_secret_key
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/your_db
UPLOAD_FOLDER=uploads
ADMIN_PASSWORD=supersecretadminpass
```

- If `DATABASE_URL` is omitted, the app defaults to `sqlite:///site.db`.

## Usage

1. **Run the Flask app**:
   ```bash
   python app.py
   ```
   The server will start at `http://127.0.0.1:5000/`.

2. **Access the Forum**:
   - Home: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)
   - Admin Panel: [http://127.0.0.1:5000/admin](http://127.0.0.1:5000/admin)

3. **Create Posts**:
   - Select board (`b` or `pol`).
   - Enter content, optionally attach an image.
   - Submit; toxic text will be blocked, NSFW image logic is currently a placeholder.

4. **Admin Actions**:
   - Login with your `ADMIN_PASSWORD`.
   - View, approve, or delete any post.

## Project Structure

```
the4chan/
├── app.py              
├── models.py            
├── requirements.txt     
├── .env                 
├── templates/           
│   ├── base.html       
│   ├── index.html      
│   ├── admin.html      
│   └── ...
├── static/              
│   ├── styles.css      
│   ├── script.js       
│   └── admin.js         
├── uploads/             
            
```

## Environment Variables

| Variable          | Description                                      | Default                   |
|-------------------|--------------------------------------------------|---------------------------|
| `SECRET_KEY`      | Flask session & CSRF protection                  | `supersecretkey`          |
| `DATABASE_URL`    | SQLAlchemy DB URI (MySQL or SQLite)              | `sqlite:///site.db`       |
| `UPLOAD_FOLDER`   | Directory path to save user-uploaded images      | `uploads`                 |
| `ADMIN_PASSWORD`  | Password for accessing admin panel               | `adminpassword`           |

## Notes

- **Text Moderation**: Uses `unitary/toxic-bert`. Threshold is set to `0.95` to reduce false positives.
- **Image NSFW**: Currently only extracts OpenCLIP embeddings. You can integrate a custom classifier later.
- **Filename Collisions**: Images are saved by original filename. Consider adding UUIDs for uniqueness.

## Future Improvements

- Integrate a real NSFW image classifier on top of OpenCLIP embeddings.
- Add pagination or infinite scroll for posts.
- Implement user sessions or ephemeral IDs for distinguishable posters.
- Allow image thumbnail generation and optimization.
- Dockerize the application for easy deployment.

## License

This project is open-source under the MIT License. See `LICENSE` for details.

