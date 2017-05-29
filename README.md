# lieu
lieu is a Python library for deduping venues and addresses around the world using [libpostal](github.com/openvenues/libpostal)'s international address normalization.

This is a prototype, and various aspects, particularly the locally-sensitive hashing and similarity/dupe-checking algorithms, will be moved into the C layer in libpostal proper after the implementation is tested/settled here.

## Installation
```pip install git+https://github.com/openvenues/lieu```

Note: libpostal and its Python binding are required to use this library, setup instructions [here](https://github.com/openvenues/pypostal).

## Command-line tool

The ```dedupe_geojson``` command-line tool will be installed in the environment's bin dir and can be used like so:

```
dedupe_geojson file1.geojson file2.geojson -o output_dir [--address-only]
```

## Input formats
Inputs are expected to be GeoJSON files. The command-line client works on both FeatureCollection and line-delimited GeoJSON, but for compatibility with the upcoming MapReduce version it's better to use line-delimited GeoJSON.

WoF and OSM field names are supported in this project (again: it's a prototype and may change) and are mapped to libpostal's schema.

At present, all venues are required to have the following properties:

- **name**: the venue/company/professional's name
- **street**: street name, reasonable in most countries but that assumption may need to be relaxed for e.g. Japan (where "suburb" would be the closest thing to street)
- **house_number**: needs to be parsed out into its own field. If not, feel free to use libpostal's parser to extract a house number from the street field.

Each record must also have a valid lat/lon (i.e. not Null Island) although entries within ~2-3km of each other can still be considered dupes if their names and addresses match. This should allow for even coordinates with relatively 

## Exact dupes vs. likely dupes

Addresses are not an exact science, so even the term "exact" here means "sharing at least one libpostal expansion in common". As such, "Market Street" and "Market St" would be considered exact matches, as would "Third Avenue" and "3rd Ave", etc.

For street name/house number, we require this sort of exact match, but more freedom is allowed in the venue/business name. A likely dupe may have some minor misspellings, may be missing common words like "Inc" or "Restaurant", and may use different word orders (common with professionsals e.g. "Obama, Barack" instead of "Barack Obama").

## Exampels of likely dupes

Below were some of the likely dupes extracted during a test-run using WoF/SimpleGeo and a subset of OSM venues in San Francisco:

|     Name 1        |       Name 2      |
| ----------------- | ----------------- |
| H Thomas Stein MD | Stein H Thomas MD |
| The Grateful Head | Grateful Head |
| Daja Inc | Daja |
| Mendelson House | Mendelsohn House |
| Posh Bagels | The Posh Bagel |
| Doyle Richard P DDS | Richard P Doyle DDS |
| Andrew Grant Law Office | Grant Andrew Law Office of |
| San Francisco Department of Building Inspection | Department of Building Inspection |
| Venezia Upholstry | Venezia Upholstery |
| Public Storage Inc | Public Storage |
| David Denebeim CPA | Denebeim David CPA |
| Gregory J Hampton | Hampton Gregory J Atty |
| Renbaum Joel MD | Joel Renbaum MD |
| Greenberg James MD | James Greenberg MD |
| Ruben Ruiz Jr MD | Ruiz Ruben MD Jr |
| Fazio Bill Attorney | Bill Fazio |
| Amity Markets | Amity Market |
| Kianca | Kianca Inc |
| Sweet Inspiration Bakery | Sweet Inspiration |
| Tanpopo | Tanpopo Restaurant |
| Bleu Marketing Solutions, Inc. | Bleu Marketing Solutions |
| Law Office of Rosario Hernandez | Rosario Hernandez Law Office |
| Pete's Cleaner | Pete's Cleaners |
| Buchalter Nemer Fields Younger | Buchalter Nemer Fields & Younger |
| Hotel Beresford | Beresford Hotel |
| Kobayashi James Y DDS | James Y Kobayashi DDS |
| Frisco Tattoo | Frisco Tattooing |
| Shelby & Bastian Law Offices of | Shelby & Bastian Law Offices |
| Roti India Bistro | Roti Indian Bistro |
| Steven Volpe Design | Volpe Steven Design |
| Oyaji | Oyaji Restaurant |
| Morgan Finnegan Llp | Morgan Finnegan |
| Michael K Chan MD | Chan Michael K MD |
| Guingona Michael P Law Offices | Michael P Guingona Law Offices |
| Goldberg Stinnett Meyers Davis | Goldberg Stinnett Meyers & Davis |
| Scott P Bradley MD | Bradley Scott P MD |
| The Pawbear Shop | The Pawber Shop |
| Russell Convenience | Russell's Convenience |
| Folkoff Robert O | Robert O Folkoff Inc |
| Sullivan Dennis M Law Offices | Dennis M Sullivan Law Offices |
| Brough Steven O DDS | Steven O Brough Inc |
| The Courtyard On Nob Hill | Courtyard On Nob Hill |
| Cohen-Lief Cardiology Medical Group | Cohen-Lief Cardiology Medical |
| Higher Grounds Coffee House and Restaurant | Higher Grounds Coffee House |
| Guido J Gores Jr MD | Guido J Gores, MD |
| Henn Etzel & Moore Inc | Henn Etzel & Moore |
| Dakota Hostel | Dakota Hotel |
| A&A Hair Design | A & A Hair Design |
| Denise Smart, MD | Smart Denise MD |
| Linda G Montgomery CPA | Montgomery Linda G CPA |
| Paul F Utrecht Law Offices | Utrecht Paul F |
| The New Nails | New Nails |
| Brian J Har Law Offices | Har Brian J |
| The Sausage Factory | Sausage Factory Inc |
| Andrews Brian T MD | Brian T Andrews MD |
| Miraloma Elementary School | Mira Loma Elementary School |
| Santos Benjamin S Law Office of | Benjamin S Santos Law Office |
| David K Marble Law Offices | Law Offices of David K Marble |
| Balboa Theatre | Balboa Theater |
| Ruth K Wetherford PHD | Wetherford Ruth K PHD |
| Nanyang Commercial Bank | Nanyang Commercial Bank LTD |
| Susan Petro | Petro Susan Atty |
| Ambassador Toys | Ambassador Toys LLC |
| Law Offices of Peter S Hwu | Peter S Hwu Law Offices |
| Wing K Lee MD | Lee Wing K MD |
| Lewis Ronel L MD | Ronel L Lewis MD |
| The Sandwich Place | Sandwich Place |
| Alvin G Buchignani Law Offices | Buchignani Alvin G |
| Thorn Ewing Sharpe & Christian | Thorn Ewing Sharpe & Christian Law Offices of |
| Books and Bookshelves | Books & Bookshelves |
| Doo Wash Cleaners | Doo Wash |
| Miraloma Liquors | Miraloma Liquor |
| Taylor Patrick E MD | Patrick E Taylor MD |
| Bike Kitchen | The Bike Kitchen |
| Arnold Laub Law Offices of | Arnold Laub Law Offices |
| Norm Bouton | Bouton Norm |
| 111 Minna | 111 Minna Gallery |
| Rosenblatt Erica Atty | Erica Rosenblatt |
| Ace USA | Ace USA Inc |
| Creech Olen CPA | Olen Creech CPA |
| Sidney R Sheray Law Office | Sheray Sidney R Law Office of |
| Quan Chen Law Offices | Law Offices of Quan Chen |
| Charles Schwab | Charles Schwab & Co |
| Sloane Square Salon | Sloane Square Beauty Salon |
| Beanery | The Beanery |
| Wesley R Higbie Law Offices | Higbie Wesley R Law Offices of |
| Meyers Ray H DDS | Ray H Meyers Inc |
| Long Elizabeth D Law Office of | Elizabeth D Long Law Office |
| Francis J Kelly | Kelly Francis J Atty |
| Equant Inc | Equant |
| Martin Douglas B Atty Jr | Douglas B Martin Jr |
| Bucay Lilliana DDS | Liliana Bucay DDS |
| Wayne's Liquors | Wayne's Liquor |
| Moore & Browning Law Office | Moore & Browning Law Offices of |
| Cai Lai Fu L A C D O M | Cai Lai Fu LACDOM |
| Center For Aesthetic Dentistry | The Center For Aesthetic Dentistry |
| Whitehead & Porter Llp | Whitehead & Porter |
| Juliati Jones DDS | Jones Juliati DDS |
| Chang Shik Shin Law Offices | Shin Chang Shik Law Offices of |
| Sparer Alan Law Offices of | Alan Sparer Law Offices |
| Goldberg Advisers | Goldberg Advisors |
| Jewelers Choice | Jeweler's Choice Inc |
| Sam A Oryol MD | Oryol Sam A MD |
| Oscar Saddul MD | Oscar Saddul Inc |
| Gerald Lee MD | Lee Gerald MD |
| Reader's Digest Sales & Svc | Readers Digest Sales & Services |
| Kerley Construction | Kerley Construction Inc |
| Laguna Honda Hospital And Rehabilitation Center | Laguna Honda Hospital & Rehabilitation | Center |
| Mission Bicycle Company | Mission Bicycle |
| Sunset Music | Sunset Music Co |
| Tafapolsky & Smith | Tafapolsky & Smith Llp |
| Alaris Group | Alaris Group LLC |
| Yummy Bakery & Cafe | Yummy Bakery and Cafe |
| Hotel Bijou San Francisco | Hotel Bijou |
| Thomas Worth Attorney At Law | Worth Thomas Attorney At Law |
| Powell Joseph E Law Offices of | Joseph E Powell Law Offices |
| J & J Bakery | J&J Bakery |
| Thomas C Bridges DDS | Bridges Thomas C DDS |
| 450 Sansome | 450 Sansome Street |
| BLOOMING ALLEY | A Blooming Alley |
| McCormack Bruce M MD | McCormack Bruce MD |
| Atlas Cafe | The Atlas Cafe |
| Maxfield's House of Caffeine | Maxfield's House of Caffiene |
| Aspen Furniture Inc | Aspen Furniture |
| Anja Freudenthal Law Offices | Freudenthal Anja Law Offices of |
| Gonzalez Gilberto A DDS | Gilberto A Gonzalez DDS |
| Great Wall Hardware | Great Wall Hardware Co |
| PO Plus | P O Plus |
| The Church in San Francisco | Church In San Francisco |
| 1550 Hyde | 1550 Hyde Cafe |
| Lampart Abe Law Office of | Abe Lampart Law Office |
| Bruce W Leppla | Leppla Bruce W Atty |
| Geoffrey C Quinn MD | Quinn Geoffrey C MD |
| Peet's Coffee & Tea | Peet's Coffee and Tea |
| Daniel Ray Bacon Law Offices | Bacon Daniel Ray Law Offices of |
| POP Interactive | Pop Interactive Inc |
| Noel H Markley DDS | Markley Noel H DDS |
| Golden Gate Theater | Golden Gate Theatre |
| San Francisco Massage Supply | San Francisco Massage Supply Co |
| Furth Firm | Furth Firm The |
| Furth Firm | Furth Firm Llp |
| The San Francisco Wine Trading Company | San Francisco Wine Trading Company |
| Sun Maxim's | Sun Maxim's Bakery |
| Kipperman Steven M Atty | Steven M Kipperman |
| Pollat Peter A MD | Peter A Pollat MD |
| Whisky Thieves | Whiskey Thieves |
| Fujimaya-ya | Fujiyama-ya |
| Solrun Computer Sales and Services | Solrun Computer Sale & Services |
| Beauty and the Beast | The Beauty and Beasts |
| Maxfield's House of Caffeine | Maxfield's House of Caffiene |
| George Bach-Y-Rita MD | Bach-Y-Rita George MD |
| The Rafael's | Rafael's |
| Gold Bennett Cera & Sidener | Gold Bennett Cera & Sidener Llp |
| Elbert Gerald J | Gerald J Elbert |
| The Frame And Eye Optical | Frame & Eye Optical |
| Bear Stearns | Bear Stearns & Co Inc |
| Lucas Law Firm | The Lucas Law Firm |
| Victoria Argumedo Law Office | Argumedo Victoria the Law Office of |
| SOMA Networks | Soma Networks Inc |
| Chang Kenneth MD | Kenneth Chang MD |
| Paul Behrend Law Office | Law Office of Paul Behrend |
| Seyfarth Shaw LLP | Shaw Seyfarth |
| La Boulange de Cole Valley | La Boulange de Cole |
| The Buccaneer | Buccaneer |
| Mikys Collection | Miky's Collections |
| Best Western Americana Hotel | Best Western Americania |
| Morris D Bobrow | Bobrow Morris D Atty |
| Marvin's Cleaner | Marvin's Cleaners |
| Older Womens League San | Older Women's League |
| Blue Plate | The Blue Plate |
| Harvey Hereford | Hereford Harvey Atty |
| The Prado Group | Prado Group Inc |
| Daily Beauty Salon and Spa | Daily Beauty Salon & Spa |
| Ho Lin MD | Lin Ho Inc |
| Sean Kafayi DDS | Kafayi Sean DDS |
| Linda Stoick Law Offices | Stoick Linda Law Office of |
| William H Goodson III MD | Goodson William H MD III |
| Edward Y Chan MD | Chan Edward Y C MD |
| Chao Peter Law Offices of | Peter Chao Law Offices |
| Tacos Los Altos | Taco Los Altos Catering |
| One Leidesdorff | One Leidsdorff |
| Carmine F. Vicino | Carmine F. Vicino, DDS |
| Hobart Building | Hobart Building Office |
| Artistry Hair & Beauty Works | Artistry Hair and Beauty Works |
| San Francisco Daily Journal | Daily Journal |
| Balboa Produce Market | Balboa Produce |
| Curtis Raff, DDS | Dr. Curtis Raff, DDS |
| Kane Harold B CPA | Harold B KANE CPA |
| All Season Sushi Bar | All Season Sushi |
| Lo Savio Thomas | Thomas J Lo Savio |
| Dolma Inc | Dolma |
| Christina L Angell Law Offices | Angell Christina Law Offices of |
| Hotel Beresford Arms | Beresford Arms Hotel |
| Lam Hoa Thun | Lam Hoa Thuan |
| Pour House | The Pour House |
| Divinsky Lauren N Atty | Lauren N Divinsky |
| Alisa Quint Interior Designer | Quint Alisa Interior Design |
| Jody La Rocca At Galleria Hair Design | Jody LA Rocca At Galleria Hair |
| Jose A Portillo | Portillo Jose A Atty |
| ristorante ideal | Ristorante Ideale |
| Central Gardens Hospital for Convalescing | Central Gardens Convalescent Hospital |
| Dr. Gordon Katznelson, MD | Gordon Katznelson MD |
| Pitz Ernest DDS | Ernest Pitz DDS |
| Girard Gibbs & De Bartolomeo | Girard Gibbs & De Bartolomeo Llp |
| The Pickwick Hotel | Pickwick Hotel |
| Craig D Mukai DDS | Mukai Craig D DDS |
| Matterhorn | Matterhorn Restaurant |
| Pope Fine Builders Inc | Pope Fine Builders |
| Coggan James F DDS | James F Coggan DDS |
| Ramsay Michael A DDS | Michael A Ramsay DDS |
| Smart and Final | Smart & Final |
| Thelen Reid & Priest LLP | Thelen Reid & Priest |
| Ar Roi | Ar Roi Restaurant |
| Hansa Pate Law Offices | Law Offices of Hansa Pate |
| Morgan Lewis & Bockius | Morgan Lewis & Bockius LLP |
| Metro Cafe | Metro Caffe |
| TAP Plastics | Tap Plastics Inc |
| Brownstone | Brownstone Inc |
| Friedman Suzanne B Law Offices of | Suzanne B Friedman Law Office |
| Quality Brake Supply Inc. | Quality Brake Supply |
| Cooper Wayne B Atty | Wayne B Cooper |
| Martin D Goodman | Goodman Martin D Atty |
| Marchese Co | Marchese Co The |
| Paul B Roache MD | Paul Roache MD |
| Mandalay | Mandalay Restaurant |
| Soderstrom Susan DDS | Susan Soderstrom DDS |
| High Touch Nail Salon | High Touch Nail & Salon |
| Cary Lapidus Law Offices | Lapidus Cary S Law Offices of |
| The Ark Christian Preschool | Ark Christian Pre-School |
| Milk Bar | The Milk Bar |
| Seck L Chan Inc | Chan Seck L MD |
| Hunan Home's Restaurant | Hunan Home's |
| Grotta Glassman & Hoffman | Grotta Glassman and Hoffman |
| Jeffrey P Hays MD | Hays Jeffrey P MD |
| Steven R Barbieri Law Offices | Law Offices of Steven Barbier |
| John A Kelley | Kelley John A |
| Dolan Law Firm | The Dolan Law Firm |
| Slater H West Inc | H Slater West Inc |
| Osborne Christopher Atty | Christopher Osborne |
| Elkin Ronald B MD | Ronald B Elkin MD |
| Tipsy Pig | The Tipsy Pig |
| Automatic Transmissions | Automatic Transmission Ctr |
| The Ferster Saul M Law Office of | Saul M Ferster Law Office |
| Bertorelli Gandi Won and Behti | Bertorelli Gandi Won & Behti |
| Word Play Inc | Word Play |
| Winston & Strawn | Winston & Strawn Llp |
| Tail Wagging Pet Svc | Tail Wagging Pet Services |
| Town and Country Beauty Salon | Town & Country Beauty Salon |
| H&L Auto Repair | H & L Auto Repair |
| La Tortilla | LA Tortilla Restaurant |
| Hawkes John W Atty | John W Hawkes |
| Charles Schwab | Charles Schwab & Co |
| Kr Travels | K R Travels |
| Greg S Tolson | Tolson Greg S |
| The Pizza Place | Pizza Place |
| Community Behavioral Health Services | Community Behavioral Health |
| Ultimate Cookie | The Ultimate Cookie |
| West Potral Cleaning Center | West Portal Cleaning Center |
| Law Office of Audrey A Smith | Audrey A Smith Law Office |
| Ciao Bella Nail Salon | Ciao Bella Nails |
| Colleen Halloran MD | Halloran Colleen MD |
| Wai-Man Ma MD | MA Wai-Man MD |
| Clay Jones Apartment | Clay Jones Apartments |
| Charles Steidtmahn | Steidtmann Charles Atty |
| Kyle Bach | Bach Kyle |
| Law Office of Michael J Estep | Michael Estep Law Office |
| Safelite AutoGlass | Safelite Auto Glass |
| Ranuska Frank S MD | Frank S Ranuska MD Inc |
| All Star Hotel | Allstar Hotel |
| Klein James C MD DDS | James C Klein MD |
| FTSE Americans Inc | Ftse Americas |
| Frucht Kenneth Law Offices of | Kenneth Frucht Law Offices |
| Daane Stephen MD | Stephen Daane MD |
| Victor Barcellona DDS | Barcellona Victor A DDS |
| Randolph Stein Law Office | Stein Randolph Law Office of |
| Seebach Lydia M MD | Lydia M Seebach MD |
| Einstein Diane Interiors | Diane Einstein Interiors |
| Charles J Berger MD | Berger Charles J MD |
| Sacred Ground Coffee House | Sacred Grounds Coffee House |
| Julie Stahl MD | Stahl Julie MD |
| Chow Rosanna MD | Rosanna Chow,  MD |
| Smith Kara Ann | Kara Ann Smith |
| Gregory Chandler Law Offices | Law Office of Gregory Chandler |
| Friedman Gary MD | Gary Friedman MD |
| Ben Gurion University of the Negev | Ben Gurion University Of Negev |
| Seventh Avenue Presbyterian Church | Seventh Avenue Presbyterian |
| Louie Dexter MD | Dexter Louie Inc |
| Randall Low MD | Low Randall MD |
| Daniel Richardson Law Offices | Richardson Daniel Law Offices |
| RC Gasoline | R C Gasoline |
| John Stewart Company The | The John Stewart Company |
| Howard Eric Specter Law Office | Specter Howard Eric Law Offices of |
| Vadim Kvitash, MD PHD | Vadim Kvitash MD |
| San Francisco Scooter Center | San Francisco Scooter Centre |
| Collier Ostrom | Collier Ostrom Inc |
| Frank Z Leidman Law Offices | Leidman Frank Z Law Offices of |
| Steiner Paul J Law Offices of | Paul J Steiner Law Offices |
| Nossaman Guthner KNOX Elliott | Nossaman Guthner Knox & Elliott Llp |
| Edralin Stella M Law Office of | Stella Edralin Law Office |
| Nielsen Haley & Abbott Llp | Nielsen Haley and Abbott LLP |
| Consulate General of People's Republic of China, San Francisco | Consulate General of the | People's Republic of China |
| Booska Steven Law Offices of | Steven A Booska Law Office |
| Jai Ho Indian Grocery Store | Jai Ho Indian Grocery |
| Wayne D Del Carlo DDS | Del Carlo Wayne D DDS |
| A C Heating & Air Condition | A C Heating & Air Conditioning Services |
| Brook Radelfinger Law Office | Radelfinger Brook Law Office of |
| Russell G Choy DDS | Choy Russell G DDS |
| Geoffrey Quinn MD | Quinn Geoffrey C MD |
| Russell's Convenience | Russell Convenience |
| Scor Reinsurance | SCOR Reinsurance Co |
| Fix My Phone | Fix My Phone SF |
| Maryann Dresner | Dresner Maryann Atty |
| May William Atty | William May |
| Thomas Lewis MD | Lewis Thomas MD |
| Turek Peter MD | Peter Turek MD |
| Nancy L Snyderman MD | Snyderman Nancy MD |
| Koncz Lawrence Atty | Lawrence Koncz |
| 24hour Fitness | 24 Hour Fitness |
| Peet's Coffee & Tea | Peet's Coffee & Tea Inc |
| B J Crystal Inc | B J Crystal |
| David B Caldwell | Caldwell David B Atty |
| Prophet Francine CPA | Francine Prophet CPA |
| Burton M Greenberg | Greenberg Burton M Atty |
| Gin Yuen T Atty | Yuen T Gin Inc |
| Norton & Ross Law Offices | Law Offices of Norton & Ross |
| Lauretta Printing & Copy Center | Lauretta Printing Company & Copy Center |
| Armstrong’s Carpet and Linoleum | Armstrong Carpet & Linoleum |
| Kokjer Pierotti Maiocco & Duck | Kokjer Pierotti Maiocco & Duck Llp |
| Payless ShoeSource | Payless Shoe Source |
| Pakwan | Pakwan Restaurant |
| Performance Contracting Inc | Performance Contracting |
| Salentine David M Atty | David M Salentine |
| W Vernon Lee PHD | Lee W Vernon Phd |
| Sanrio Inc | Sanrio |
| Eric L Lifschitz Law Offices | Lifschitz Eric L Offices of |
| Denise Smart MD | Smart Denise MD |
| Saddul Oscar A MD | Oscar Saddul Inc |
| Noble Warden H DDS | H Warden Noble DDS |
| Michael Papuc Law Offices | Law Offices of Michael Papuc |
| Main Elliot MD | Elliott Main, MD |
| Leslie Campbell MD | Campbell Leslie MD |
| FedEx Office Print and Ship Center | FedEx Office Print & Ship Center |
| People PC Inc | People PC |
| Dodd Martin H Atty | Martin H Dodd |
| X M Satellite | Xm Satellite |
| Normandie Hotel | Normandy Hotel |
| Campton Place Hotel | Campton Place |
| Kaiser U Khan Law Offices | Khan Kaiser U Law Offices of |
| David L Rothman DDS | Rothman David L DDS |
| Mortgage Management Syste | Mortgage Management Systems |
| The Music Store | Music Store |
| Dr. Stephanie Jee DDS | Jee Stephanie DDS |
| Tasana Hair Design | Tasanas Hair Design |
| Ling Ling Cuisine | Ling Ling Cuisne |
| FedEx Office Print and Ship Center | FedEx Office Print & Ship Center |
| Margaret Tormey Law Offices | Tormey Margaret Law Offices of |
| Hoi's Construction Inc | Hoi's Construction |
| Bny Western Trust Company Inc | BNY Western Trust Co |
| Anthony Portale MD | Portale Anthoney MD |
| Charles Schwab | Charles Schwab & Co |
| Daniel Raybin MD | Raybin Daniel MD |
| Pearl's Deluxe Burgers | Pearls Delux Burgers |
| Geoffrey Rotwein Law Offices | Rotwein Geoffrey |
| Crawford David J DDS | David J Crawford DDS |
| Effects | Effects Design |
| Jacobs Spotswood Casper | Jacobs Spotswood Casper & Murphy |
| Charles Seaman MD | Seaman Charles MD |
| Wenger Phillip M | Phillip M Wenger CPA |
| NBC Kntv | NBC Kntv San Francisco |
| Law Offices of Anthony Head | Anthony Head Law Offices |
| Pizzetta 211 | Pizzetta 211 Coffee |
| New Liberation Presbyterian Church | New Liberation Presbyterian |
| JNA Trading Co | Jna Trading Co Inc |
| The San Francisco Foundation | San Francisco Foundation |
| Girard & Equitz | Girard & Equitz Llp |
| Kenneth Louie CPA | Louie Kenneth CPA |
| Terroir Natural Wine Merchant & Bar | Terroir Natural Wine Merchant |
| Richard K Lee CPA | Lee Richard K CPA |
| Red Coach Motor Lodge | The Red Coach Motor Lodge |
| Peter Goodman Law Offices | Goodman Peter Law Offices of |
| Pete's Union 76 | Pete's Union 76 Service |
| Skaar Furniture | Skaar Furniture Assoc Inc |
| Barbara Giuffre Law Office | Giuffre Barbara Law Offices of |
| The Valley Tavern | Valley Tavern |
| Katz Louis S Law Offices of | Louis S KATZ Law Offices |
| Ditler Real Estate | Dittler Real Estate |
| Doyle Richard H Jr DDS | Richard H Doyle Jr DDS |
| King Ling | King Ling Restaurant |
| Charon Thom DDS | Thom Charon DDS |
| Atlas DMT | Atlas D M T |
| Epstein Englert Staley Coffey | Epstein Englert Staley & Coffey |
| League of Women Voters of S F | League Of Women Voters |
| Dennis P Scott Atty | Scott Dennis P Atty |
| Richards Peter C MD | Peter C Richards Inc |
| Foot Reflexology | Foot Reflexology Center |
| Marquez Law Group LLP | Marquez Law Group |
| Dr. Jamie Marie Bigelow | Bigelow Jamie Marie MD |
| Saida & Sullivan Design Partners | Saida & Sullivan Design |
| Employment Law Training Inc | Employment Law Training |
| Matt's Auto Body | Matt's Auto Body Shop |
| David N Richman MD | Richman David N MD |
| Squat & Gobble | Squat And Gobble |
| The Lost Ladles Cafe | Lost Ladle Cafe |
| Kail Brian DDS | Brian Kail DDS |
| Phuket Thai Restaurant | Phuket Thai |
| US Trust | US Trust Co |
| Godiva Chocolatier | Godiva Chocolatier Inc |
| Warren Sullivan | Sullivan Warren Atty |
| Renbaum Joel MD | Joel Renbaum MD |
| Law Offices of Arnold Laub | Arnold Laub Law Offices |
| David L Chittenden MD Inc | Chittenden David L MD |
| Ling Kok-Tong MD | Kok-Tong Ling MD |
| Rudy Exelrod & Zieff Llp | Rudy Exelrod & Zieff |
| Universal Electric Supply | Universal Electric Supply Company |
| Carpenter Rigging & Supply | Carpenter Rigging |
| Sandy's Cleaners | Sandy Cleaners |
| Mark Wasacz Attorney | Wasacz Mark Attorney |
| John Leung DDS | Leung John DDS |
| Alberto Lopez MD | Lopez Alberto MD |
| Catherine Kyong-Ponce MD | Kyong-Ponce Catherine MD |
| Pereira Aston & Associates | Aston Pereira & Assoc |
| Bernard Alpert, MD | Bernard S Alpert MD |
| Nicholas Carlin Law Offices | Law Offices of Nicholas Carlin |
| The Humidor | Humidor |
| MMN Plumbing | M M N Plumbing |
| Club 26 Mix | 26 Mix |
| Citrus Club | The Citrus Club |
| Perkins Beverly J DDS | Beverly J Perkins DDS |
| Body Manipulation | Body Manipulations |
| Richard Delman PHD | Delman Richard PHD |
| Mitchell Bruce T | Bruce T Mitchell |
| Law Office of Gross Julian | Julian Gross Law Office |
| All Rooter Plumbing Needs | All Rooter & Plumbing Needs |
| New Tsing Tao | New Tsing Tao Restaurant |
| Law Office of Nelson Meeks | Meeks Nelson Law Offices |
| Nouvelle Tailor and Laundry Service | Nouvelle Tailor & Laundry Service |
| King & Kelleher | King & Kelleher Llp |
| Robert S Gottesman | Gottesman Robert S Atty |
| McGuinn Hillsman & Palefsky | Mc Guinn Hillsman & Palefsky |
| S F Japanese Language Class | Sf Japanese Language Class |
| Elins Eagles-Smith Gallery Inc | Elins Eagles-Smith Gallery |
| ATM Travel | Atm Travel Inc |
| Rocket Careers | Rocket Careers Inc |
| Alyce Tarcher Bezman MD | Tarcher Alyce Bezman MD |
| Carlo Andreani | Andreani Carlo Atty |
| Frank R Schulkin MD | Schulkin Frank R MD |
| Marjorie A Smith, MD | A Marjorie Smith MD |
| The Last Straw | Last Straw |
| Dyner Toby S MD | Toby Dyner MD |
| Frankel J David PHD | J David Frankel PHD |
| J David Gladstone Institutes | J David Gladstone Institute |
| Specceramics Inc | Specceramics |
| Hotel Embassy | Embassy Hotel |
| Meeks Nelson Law Offices of | Meeks Nelson Law Offices |
| Ponton Lynne E MD | Lynn E Ponton MD |
| Evergreen Realty Inc | Evergreen Realty |
| Stewart J Investments | J Stewart Investments |
| Kao Samuel MD | Samuel D Kao MD |
| Kao Samuel MD | Samuel Kao MD |
| Dickstein Jonathan S | Jonathan S Dickstein |
| Melitas Euridice DDS | Euridice Melitas DDS |
| Levy Peter L | Peter L Levy |
| Bnp Paribas Inc | BNP Paribas |
| 365 Main | 365 Main Inc. |
| McKinney Tres Design | Mc Kinney Tres Design |
| Law Offices of Cheryl A Frank | Cheryl A Frank Law Office |
| 24 Guerrero | 24 Guerrero Cleaners |
| Garden Court | The Garden Court |
| IKON Office Solutions | Ikon Office Solutions Inc |
| Russack Neil W MD | Neil W Russack MD |
| Turtle Tower Restaurant | Turtle Tower Retaurant |
| Best Western Americana Hotel | Best Western Americania |
| Stitcher | Stitcher, Inc |
| Greenwald Alan G MD | Alan G Greenwald MD |
| Tartine Bakery | Tartine Bakery & Cafe |
| Bath & Body Works Inc | Bath & Body Works |
| Kao-Hong Lin MD | Lin Kao-Hong MD |
| Lundgren-Archibald Group | Lundgren Group |
| Chien Chau Chun MD | Chau Chun Chien MD |
| Litton & Geonetta Llp | Litton & Geonetta |
| Ecuador Consulate General | Consulate General Of Ecuador |
| The Store On the Corner | Store On The Corner |
| Jackson Square Law Offices | The Jackson Square Law Office |
| Ranchod Kaushik Law Offices of | Kaushik Ranchod Law Offices |
| Sue Hestor | Hestor Sue Atty |
| Euro Gems Inc | Euro Gems |
| C L Keck Law Office | Law Offices of C L Keck |
| Sekhon & Sekhon Law Office | Sekhon & Sekhon Law Office of |
| Telegraph Hill Family Medical | Telegraph Hill Family Medical Group |
| Tu Lan Restaurant | Tu Lan |
| Fisk Albert A MD | Albert A Fisk MD |
| Lee & Uyeda Llp | Lee & Uyeda |
| Hood Chiropractic and Physical Therapy | Hood Chiropractic & Physical Therapy |
| Sylvan Learning | Sylvan Learning Center |
| Herbstman Stephen CPA | Stephen Herbstman CPA |
| Pacific Hematology Oncology Associates | Pacific Hematology & Oncology |
| Marla J Miller | Miller Marla J |
| Cannon Constructors Inc | Cannon Constructors |
| ThirstyBear Brewing Company | Thirsty Bear Brewing Company |
| Intercall Inc | Intercall |
| Colman Peter J Atty | Peter J Colman |
| Notre Dame Des Victoires Church | Notre Dame des Victoires |
| KIRK B Freeman Law Offices | Law Offices of Kirk B Freeman |
| Cafe Tosca | Tosca Cafe |
| The Nite Cap | Nite Cap |
| Manora`s Thai Cuisine | Manora's Thai Cuisine |
| Ingleside Branch Library | Ingleside Branch Public Library |
| Kim Son | Kim Son Restaurant |
| First Samoan Congregational Church | First Samoan Congregational |
| Sara A Simmons Law Offices | Simmons Sara A Law Offices of |
| Epstein Robert J | Robert J Epstein MD |
| Blazing Saddles Bike Rental | Blazing Saddles Bike Rentals |
| Scarpulla Francis O Atty | Francis O Scarpulla |
| Sabella & LaTorre | Sabella & La Torre |
| Oyama Karate | World Oyama Karate |
| Jung & Jung Law Offices | The Law Offices of Jung and Jung |
| Greenhouse | Greenhouse Cafe |
| The Chieftain Irish Pub | The Chieftain Irish Pub & Restaurant |
| Forsyth Hubert D Atty | Hubert D Forsyth |
| Timothy D Regan Jr | Regan Timothy D Atty Jr |
| Public Storage | Public Storage Inc |
| Aspect Custom Framing | Aspect Custom Framing & Gallery |
| Hotel Phillips | Philips Hotel |
| Toad Hall | Toad Hall Bar |
| Chen Theodore C Law Offices | Theodore C Chen Law Office |
| Tim A Pori Attorneys At Law | Pori Tim Attorney At Law |
| Al's Good Food | Al's Cafe Good Food |
| Little Beijing | Little Beijing Restaurant |
| Alkazin John J Atty | John J Alkazin |
| Great Eastern Restaurant | Great Eastern |
| Michael A Mazzocone | Mazzocone Michael A Atty |
| Chris R Redburn Law Offices | Redburn Chris R Law Offices of |
| Chuk W Kwan Inc | Kwan Chuk W MD |
| The Urban Farmer Store | Urban Farmer Store |
| Michael Parratt, DDS | Michael Parrett, DDS |
| A Cosmetic Surgery Clinic | Cosmetic Surgery Clinic |
| Holiday Cleaner | Holiday Cleaners |
| Business Investment Management, Inc | Business Investment Management |
| Arthur Chambers | Chambers Arthur Atty |
| Touchstone Hotel | The Touchstone Hotel |
| Bresler & Lee Law Offices of | Bresler & Lee Law Offices |
| Shen Kee Bakery | Sheng Kee Bakery |
| Zaloom Vivian W Atty | Vivian W Zaloom |
| Park Presidio United Methodist Church | Park Presidio United Methodist |
| Mercedes-Bemz of San Francisco | Mercedes-Benz of San Francisco |
| Hall Kelvin W DDS | Kelvin W Hall DDS |
| Kurt Galley Jewelers | Gallery Kurt Jewelers |
| PKF Consulting | P K F Consulting |
| Fti Consulting Inc | FTI Consulting |
| Val de Cole Wines and Spirits | Val De Cole Wines & Spirits |
| Episode Salon and Spa | Episode Salon & Spa |
| Copy Station Inc | Copy Station |
| Cafe Nook | Nook |
| Consulate General Of Honduras | Honduras Consulate General of |
| E David Manace MD | Manace E David MD |
| Dan Yu Carpet Company | Dan Yu Carpet Company Inc |
| Jeong Steve M | Steve M Jeong Realty |
| Star Bagels | Star Bagel |
| Edward A Puttre Law Office | Puttre Edward A Law Offices of |
| Mozzarella di Bufala | Mozzarella Di Bufala Pizzeria |
| Knudsen Derek T Law Offices of | Derek T Knudsen Law Offices |
| Nielsen Haley & Abbott | Nielsen Haley and Abbott LLP |
| Michael A Futterman | Futterman Michael A Atty |
| Bush Robert A MD Jr | Robert A Bush Jr MD |
| Istituto Italiano di Cultura | Istituto Italiano di Cultura di San Francisco |
| Allen F Smoot Inc | Smoot Allen F MD |
| Ronald P St Clair | St Clair Ronald P Atty |
| John M Jemerin MD | Jemerin John M MD |
| Choice For Staffing | The Choice For Staffing |
| Lillie A Mosaddegh MD | Mosaddegh Lillie A |
| Morgan & Finnegan | Morgan Finnegan |
| William M Balin | Balin William M Atty |
| A Party Staff | Party Staff Inc |
| Watanabe Aileen N MD | Aileen Watanabe, MD |
| Amoeba Music | Amoeba Music Inc |
| Pinard Donald CPA | Donald Pinard CPA |
| Adco Group Inc | ADCO Group |
| William J Hapiuk | Hapiuk William J |
| Kaplan Paul M Atty | Paul M Kaplan |
| Braunstein Mervin J DDS | Mervin J Braunstein DDS |
| Bay Capital Legal Group | Bay Capital Legal |
| Sell West Inc | Sell West |
| Hamms Building | The Hamms Building |
| Lauren Standig MD | Standig Lauren MD |
| William D Rauch Jr | Rauch William D Atty Jr |
| Stephen D Finestone Law Office | Finestone Stephen D Law Offices of |
| Robert T Imagawa DDS | Imagawa Robert T DDS |
| The Flower Girl | Flower Girl |
| Richard K Bauman | Bauman K Richard Atty |
| Arcpath Project Delivery | Arcpath Project Delivery Inc |
| Samuel Ng CPA | Ng Samuel CPA |
| Reverie Cafe | Cafe Reverie |
| Fibrogen Inc | FibroGen |
| Michelangelo Caffe | Michelangelo Cafe |
| Leslie C Moretti MD Inc | Moretti Leslie C MD |
| Jonathan Blaufarb Law Ofc | Blaufarb Jonathan Law Ofc of |
| Swati Hall Law Office | Law Office of Swati Hall |
| Sushi Boat | Sushi Boat Restaurant |
| Sisters Salon & Spa | Sisters Salon and Spa |
| Boyle William F MD | William F Boyle MD |
| Bucay Liliana DDS | Liliana Bucay DDS |
| Cahill Contractors Inc | Cahill Contracting Co |
| Banez Maryann MD | Maryann Banez MD |
| Saigon Sandwich | Saigon Sandwich Shop |
| Parkside Wash & Dry | Parkside Wash and Dry |
| Gilbert J Premo | Premo Gilbert J Atty |
| Klaiman Kenneth P Atty | Kenneth P Klaiman |
| MMC Wine & Spirit | MMC Wine & Spirits |
| Little Henry's | Little Henry's Restaurant |
| Ho's Drapery Inc | Ho's Drapery |
| House of Hunan Restaurant | House Of Hunan |
| Gerald S Roberts MD | Roberts Gerald S MD |
| Sunset Supermaket | Sunset Supermarket |
| Jamie Marie Bigelow MD | Bigelow Jamie Marie MD |
| Michael M Okuji DDS | Michael Okuji, DDS |
| Mustacchi Piero O MD | Piero O Mustacchi MD |
| Tricolore | Tricolore Cafe |
| Bloom International Relocations, Inc. | Bloom International Relocation |
| Kostant Arlene Atty | Arlene Kostant |
| Jerome Garchik | Garchik Jerome Atty |
| Shu-Wing Chan MD | Chan Shu-Wing MD |
| Squires Leslie A MD | Leslie A Squires MD |
| Ping F Yip Chinese Acupressure | Yip Ping F Chinese Acupressure |
| Li Suzanne G MD | Suzanne G Li MD |
| Asia Pacific Groups | Asia Pacific Group |
| O'Melveny & Myers LLP | OMelveny & Myers LLP |
| Cafe Chaat | Chaat Cafe |
| Gross & Belsky | Gross & Belsky Llp |
| Cybelle's Front Room | Cybelle's Front Room Pizza |
| Coopersmith Richard MD | Richard C Coopersmith MD |
| Daniel Feder Law Offices | Feder Daniel Law Offices of |
| Maloney Alan MD | Alan Maloney MD |
| US Parking | U S Parking |
| Miller Brown Dannis | Miller Brown & Dannis |
| Michael D Handlos | Handlos Michael D Atty |
| Hotel Chancellor | Chancellor Hotel |
| Haines & Lea Attorneys-Law | Haines & Lea Attorneys At Law |
| M H Construction | Mh Construction |
| Samuel D Kao MD | Samuel Kao MD |
| Savor | Savor Restaurant |
| FedEx Office Print and Ship Center | FedEx Office Print & Ship Center |
| Law Offices of Maritza B Meskan | Maritza B Meskan Law Office |
| Blade Runners Hair Studio | Bladerunners Hair Studio |
| Rita L Swenor | Swenor Rita L |
| Michael Harrison MD | Harrison Michael MD |
| Adam F Gambel Attorney At Law | Gambel Adam F Attorney At Law |
| Odenberg Ullakko Muranishi | Odenberg Ullakko Muranishi & Company Llp |
| Days Inn San Francisco At The Beach | Days Inn at the Beach |
| La Tortilla | LA Tortilla Restaurant |
| Snyder Miller & Orton LLP | Snyder Miller & Orton |
| Happy Donut | Happy Donuts |
| Goldman Sachs | Goldman Sachs & Co |
| Roger S Kubein Law Offices | Kubein Roger S Law Offices of |
| Panta Rei Restaurant | Panta Rei Cafe Restaurant |
| Accent International Study Abroad | Accent Study Abroad |
| Matthew D Hannibal MD | Hannibal Mathew D MD |
| Branch John W CPA | John W Branch CPA |
| Randolph Johnson Design | Johnson Randolph Design |
| Dr. Rita Melkonian, MD | Melkonian Rita MD |
| Chavez Marco DDS | Marco Chavez DDS |
| New Eritrean Restaurant & Bar | New Eritrea Restaurant & Bar |
| Terence A Redmond Law Offices | Redmond Terence A Law Offices of |
| BrainWash Cafe | Brainwash |
| Judy Silverman MD | Silverman Judy MD |
| Golden 1 Credit Union | The Golden 1 Credit Union |
| Henry's Hunan Restaurant | Henry's Hunan |
| Kronman Craig H Atty | Craig H Kronman |
| Kaiser Permanente Medical Center San Francisco | Kaiser Permanente Medical Center |
| Sigaroudi Khosrow DDS Ms | Khosrow Sigaroudi DDS |
| Janes Capital Partners Inc | Jane Capital Partners |
| Royal Cleaners | Royal Cleaner |
| Dennis L Hamby MD | Hamby Dennis L MD |
| Dorinson S Malvern MD | S Malvern Dorinson MD |
| Gladstone & Assocs | Gladstone & Assoc |
| Curry Roy L MD | Roy L Curry Inc |
| Leung Eric L MD | L Eric Leung MD |
| Eureka Theatre | Eureka Theatre Company |
| J C Lee CPA | Lee J C CPA |
| Szechuan Taste | Szechuan Taste Restaurant |
| Robert O'Brien | O'brien Robert MD |
| Steel Angela Law Offices of | Angela Steel Law Offices |
| Akiko's | Akiko's Restaurant |
| Van Ness Vallejo Market | Van Ness & Vallejo Market |
| Shalimar | Shalimar Restaurant |
| Andrew Au CPA | Au Andrew CPA |
| Chau's Pearl | Pearl Chaus Co |
| Mayor Kim R Law Offices | Kim R Mayor Law Offices |
| Bruyneel & Leichtnam Attorneys At Law | Bruyneel & Leichtnam Attorney |
| Petra Cafe | Cafe Petra |
| Lannon Richard A MD | Richard A Lannon MD |
| Milliman USA | Milliman U S A |
| James W Haas | Haas James W Atty |
| Galleria Newsstand | The Galleria Newsstand |
| Delagnes Mitchell & Linder | Delagnes Mitchell & Linder Llp |
| Keith Brenda Cruz Law Offices of | Brenda Cruz Keith Law Offices |
| Miraloma Elementary School | Mira Loma Elementary School |
| Dubiner Bennett DDS | Bennett Dubiner DDS |
| Attruia-Hartwell Amalia | Amalia Attruia-Hartwell, Attorney |
| P&R Beauty Salon | P & R Beauty Salon |
| Martin C Carr MD | Carr Martin C MD |
| Wong Robert Law Offices of | Robert Wong Law Offices |
| John A Lenahan Inc | Lenahan John A MD |
| Khan Salma S MD | Salma S Khan MD |
