# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core.Plugin.FlwBasePlugin import FlwBasePlugin


class BFlix(FlwBasePlugin):
    name        = "BFlix"
    language    = "en"
    main_url    = "https://fmovies.llc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch free Streaming movies and TV shows online in HD quality. You can also Download movies for free here on Fmovies website"

    main_page   = {
        f"{main_url}/movie?page="                  : "Movies",
        f"{main_url}/tv-show?page="                : "TV Shows",
        f"{main_url}/top-imdb?page="               : "Top IMDB",
        f"{main_url}/genre/action?page="           : "Action",
        f"{main_url}/genre/action-adventure?page=" : "Action & Adventure",
        f"{main_url}/genre/adventure?page="        : "Adventure",
        f"{main_url}/genre/animation?page="        : "Animation",
        f"{main_url}/genre/biography?page="        : "Biography",
        f"{main_url}/genre/comedy?page="           : "Comedy",
        f"{main_url}/genre/crime?page="            : "Crime",
        f"{main_url}/genre/documentary?page="      : "Documentary",
        f"{main_url}/genre/drama?page="            : "Drama",
        f"{main_url}/genre/family?page="           : "Family",
        f"{main_url}/genre/fantasy?page="          : "Fantasy",
        f"{main_url}/genre/history?page="          : "History",
        f"{main_url}/genre/horror?page="           : "Horror",
        f"{main_url}/genre/kids?page="             : "Kids",
        f"{main_url}/genre/music?page="            : "Music",
        f"{main_url}/genre/mystery?page="          : "Mystery",
        f"{main_url}/genre/news?page="             : "News",
        f"{main_url}/genre/reality?page="          : "Reality",
        f"{main_url}/genre/romance?page="          : "Romance",
        f"{main_url}/genre/sci-fi-fantasy?page="   : "Sci-Fi & Fantasy",
        f"{main_url}/genre/science-fiction?page="  : "Science Fiction",
        f"{main_url}/genre/soap?page="             : "Soap",
        f"{main_url}/genre/talk?page="             : "Talk",
        f"{main_url}/genre/thriller?page="         : "Thriller",
        f"{main_url}/genre/tv-movie?page="         : "TV Movie",
        f"{main_url}/genre/war?page="              : "War",
        f"{main_url}/genre/war-politics?page="     : "War & Politics",
        f"{main_url}/genre/western?page="          : "Western",
    }
