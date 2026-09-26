# Ntheemba Centralized Product Catalog

## Vision, Architecture, Goals, and Next Steps

**Status:** Initial Product Vision\
**Primary ecosystem:** TradeFlow and Ntheemba\
**Initial focus:** Retail & Grocery and Salon & Beauty\
**Future expansion:** Bars & Liquor Stores, Restaurants, Pharmacies, and
other business types

------------------------------------------------------------------------

## 1. The Goal

The goal is to build a **centralized product catalog** that acts as a
shared product knowledge system for TradeFlow, Ntheemba, and future
applications.

Today, when a business starts using a business management system, it may
have to manually create every product. The owner may need to enter the
product name, category, unit, barcode, description, and other
information one product at a time.

The centralized catalog will reduce this work.

A business owner should be able to:

1.  Search for or scan a product.
2.  Select the correct product or variant.
3.  Let the system automatically fill in the standard product
    information.
4.  Enter only the information that is unique to their business, such
    as:
    -   Unit cost
    -   Selling price
    -   Opening stock
    -   Minimum or maximum stock levels
    -   Supplier information, when needed

The simple idea is:

> **No business should have to create common product information from
> zero if that product is already known by the Ntheemba ecosystem.**

------------------------------------------------------------------------

## 2. The Central Catalog and the Business Database Are Different

The system should separate **shared product facts** from
**business-specific information**.

### Centralized catalog information

The central catalog can contain information such as:

-   Permanent catalog ID
-   Business type
-   Category
-   Subcategory
-   Manufacturer
-   Brand
-   Product name
-   Product family
-   Variant
-   Flavor
-   Size
-   Unit
-   Packaging type
-   Product type
-   Manufacturer barcode, when available
-   Ntheemba-generated barcode, when needed
-   Product image reference
-   Source image URL
-   Product description
-   Verification status
-   Source information

### Business-specific information

Each TradeFlow business should keep its own information, such as:

-   Local display name
-   Unit cost
-   Selling price
-   Current stock
-   Opening stock
-   Reorder level
-   Maximum stock
-   Supplier
-   Batch information
-   Stock movements
-   Business-specific notes

This separation is important because a Coca-Cola product may be the same
product everywhere, but every shop may buy it at a different cost, sell
it at a different price, and hold a different amount of stock.

------------------------------------------------------------------------

## 3. Product Structure

The catalog should use a clear hierarchy.

A possible structure is:

**Business Type → Category → Subcategory → Manufacturer → Brand →
Product → Variant → Barcode**

For example:

**Retail & Grocery**\
→ Beverages\
→ Carbonated Soft Drinks\
→ Manufacturer\
→ Coca-Cola\
→ Coca-Cola\
→ Orange-flavored soft drink\
→ 500 ml bottle\
→ Barcode

The exact structure can evolve, but the most important rule is that
every product and variant should have a stable internal identity.

------------------------------------------------------------------------

## 4. Permanent Catalog IDs

Names should never be the main connection between the central catalog
and a business product.

Every catalog item should have a permanent ID.

For example:

-   Product ID: `PRD-COCA-COLA-ORANGE`
-   Variant ID: `VAR-COCA-COLA-ORANGE-500ML-PET`

A business may choose to display the product as:

-   Coca-Cola Orange 500 ml
-   Coke Orange
-   Orange Soft Drink
-   Soft Drink Coca-Cola Orange

The wording can change, but the **variant ID remains the same**.

This means TradeFlow and Ntheemba still know that all of these local
names refer to the same underlying catalog item.

### Recommended rule

-   The **central catalog name** is the standard global name.
-   The **local display name** is optional and controlled by the
    business.
-   The **catalog ID or variant ID** is the real link between the two
    systems.

------------------------------------------------------------------------

## 5. Variants

Variants are important because the same product can be sold in different
forms.

For example:

**Coca-Cola**

Possible variants:

-   300 ml can
-   500 ml bottle
-   1 litre bottle
-   2 litre bottle

Each variant should have its own permanent variant ID.

When a new user types **Coca-Cola**, TradeFlow should not force them to
understand a complicated data model. Instead, it can simply ask:

> Which one?

Then show simple choices such as:

-   500 ml bottle
-   1 litre bottle
-   2 litre bottle
-   Can

The system handles the technical variant IDs in the background.

------------------------------------------------------------------------

## 6. Catalog-Assisted Product Creation

This is one of the most important TradeFlow features enabled by the
central catalog.

When a business owner creates a new product, TradeFlow can search the
centralized catalog while the user types.

Example:

The user types:

**Coca-Cola**

TradeFlow searches the catalog and shows matching products and variants.

After the user selects the correct variant, TradeFlow can automatically
fill in shared information such as:

-   Standard product name
-   Category
-   Manufacturer
-   Brand
-   Variant
-   Size
-   Unit
-   Packaging
-   Barcode
-   Catalog ID
-   Image reference

The business owner then enters only their own information:

-   Cost
-   Selling price
-   Opening stock
-   Supplier, if needed

This can turn product creation from a long manual process into a few
seconds of work.

------------------------------------------------------------------------

## 7. Barcode Strategy

The system should support more than one type of barcode.

### Manufacturer barcode

If a product already has an official manufacturer barcode, the catalog
should store it.

### Multiple manufacturer barcodes

In some cases, the same logical product may have different valid
barcodes because of:

-   Packaging changes
-   Different markets
-   Different manufacturing locations
-   New product versions

The catalog should therefore be able to associate multiple barcodes with
the correct product or variant when necessary.

### Ntheemba-generated barcode

Some products do not naturally have a manufacturer barcode.

Examples include:

-   Tomatoes
-   Beans sold by weight
-   Kapenta
-   Vegetables
-   Loose grains
-   Repacked products
-   Locally prepared or unbranded goods

These products can still have a permanent catalog identity.

Ntheemba can generate an ecosystem barcode that businesses may use if
they want to print labels or scan the item.

However, the **permanent catalog ID should remain separate from the
barcode**. The barcode is a way to find the item; the catalog ID is its
true identity inside the system.

------------------------------------------------------------------------

## 8. Weight-Based and Bulk Products

The catalog should support different inventory behaviors.

Possible inventory types include:

-   Packaged
-   Weight-based
-   Volume-based
-   Piece-based

For example:

**Tomatoes**

The central catalog can define the product **Tomatoes** and give it a
permanent catalog ID.

A business may sell tomatoes:

-   Per kilogram
-   Per 500 grams
-   Per bag
-   Per piece

The central catalog defines what the product is. The business decides
how it sells and manages that product locally.

If the business creates a packaged version, such as **Tomatoes 1 kg**,
it may use a Ntheemba-generated barcode for that sellable unit.

------------------------------------------------------------------------

## 9. Centralized Product Images

Businesses should not have to upload the same common product image again
and again.

Product media should be stored centrally.

The central catalog can contain:

-   Main image URL
-   Thumbnail URL
-   Additional image URLs
-   Future video URLs
-   Original source URL
-   Media verification information

TradeFlow businesses should normally store only:

-   The catalog ID, or
-   A reference to the central media URL

This reduces duplicated storage and keeps client systems lightweight.

If the central image is improved later, every application using the
catalog can benefit from the improved image.

Businesses may still be allowed to use their own local image when they
need to.

------------------------------------------------------------------------

## 10. Seed JSON Files

Before the full catalog platform is built, structured JSON files can be
used as **seed data**.

These files are not necessarily the final live database.

They are more like blueprints or source files.

A seed file can contain:

-   Manufacturer
-   Brand
-   Product
-   Variant
-   Barcode
-   Category
-   Size
-   Unit
-   Packaging
-   Source URLs
-   Source image URLs
-   Verification notes

Later, the Catalog Builder can read these files and:

1.  Validate the data.
2.  Detect duplicates.
3.  Download source images.
4.  Optimize the images.
5.  Upload them to permanent centralized storage.
6.  Create permanent catalog IDs.
7.  Publish the clean product data into the production catalog.

The seed JSON is therefore the **source material**, while the production
catalog is the **clean, verified system used by applications**.

------------------------------------------------------------------------

## 11. The Catalog Builder

The Catalog Builder should be a separate internal tool used to manage
the centralized catalog.

It should eventually allow an administrator to:

-   Create business types
-   Create categories and subcategories
-   Add manufacturers
-   Add brands
-   Add products
-   Add variants
-   Add and verify barcodes
-   Import seed JSON files
-   Review duplicate products
-   Merge duplicate records
-   Review products submitted by TradeFlow businesses
-   Manage product images
-   Verify source information
-   Publish approved products
-   Update existing catalog records

The Catalog Builder is important because the catalog will continue
growing.

The goal is not to manually edit thousands of raw files forever. The
goal is to build a tool that makes maintaining the catalog easier over
time.

------------------------------------------------------------------------

## 12. Contributions From TradeFlow Businesses

Every TradeFlow installation can help improve the catalog.

When a business creates a product that is not found in the central
catalog, TradeFlow can optionally submit that product as a **catalog
candidate**.

The product should not automatically become a trusted global product.

Instead, it should enter a review queue.

The Catalog Builder can then check:

-   Is this really a new product?
-   Is it a duplicate?
-   Is the spelling correct?
-   Is the barcode valid?
-   Does the product already exist under another name?
-   Is the category correct?
-   Is the image suitable?

After review, the product can be approved and added to the central
catalog.

This creates a network effect:

> The more businesses use TradeFlow, the better the shared catalog
> becomes.

------------------------------------------------------------------------

## 13. Initial Business Types

The architecture should support many industries, but development should
begin with a small number.

### Phase 1

1.  **Retail & Grocery**
2.  **Salon & Beauty**

### Future modules

-   Bars & Liquor Stores
-   Restaurants
-   Pharmacies
-   Hardware stores
-   Other specialized businesses

Each business type can have its own categories while still using the
same central catalog engine.

------------------------------------------------------------------------

## 14. Initial Retail & Grocery Categories

Possible starting categories include:

-   Beverages
-   Water
-   Juices
-   Dairy & Eggs
-   Cooking Oil & Spices
-   Rice, Pasta & Grains
-   Mealie Meal & Flour
-   Canned & Packaged Foods
-   Snacks & Confectionery
-   Bread & Bakery
-   Household Cleaning
-   Personal Care
-   Baby Products
-   Frozen Foods
-   Fresh Produce
-   Weight-Based & Bulk Goods

The category list can improve as real businesses use the system.

------------------------------------------------------------------------

## 15. Initial Salon & Beauty Categories

Possible categories include:

-   Hair Extensions
-   Braiding Hair
-   Wigs
-   Hair Treatments
-   Shampoo & Conditioner
-   Hair Oils
-   Styling Products
-   Nail Products
-   Makeup
-   Skin Care
-   Salon Equipment
-   Beauty Accessories

The same catalog principles still apply:

**Category → Manufacturer → Brand → Product → Variant**

------------------------------------------------------------------------

## 16. How TradeFlow Uses the Catalog

TradeFlow can use the catalog for:

-   Faster business setup
-   Product search
-   Barcode scanning
-   Smart product creation
-   Automatic product information
-   Consistent product naming
-   Product images
-   Variant selection
-   Reducing duplicate product entry
-   Improving data quality

TradeFlow remains responsible for the business's private operational
data, including:

-   Stock
-   Cost
-   Price
-   Sales
-   Suppliers
-   Batches
-   Profit information

The central catalog should not need access to private business financial
information to perform its main job.

------------------------------------------------------------------------

## 17. How Ntheemba Uses the Catalog

The catalog can become a knowledge layer for Ntheemba.

For example, a customer may ask:

> Do you have Fanta?

Ntheemba can use the central catalog to understand that **Fanta** may
have several:

-   Flavors
-   Sizes
-   Packaging types
-   Variants

It can then check the specific business's TradeFlow inventory to find
out:

-   Which variants are available
-   Current stock
-   Current selling price

The central catalog explains **what the product is**.

TradeFlow explains **whether this business has it, how much it costs,
and how much stock is available**.

------------------------------------------------------------------------

## 18. How Chat E-Commerce Uses the Catalog

The same catalog can support conversational shopping.

A customer could say:

> I need a 2 litre orange soft drink.

Ntheemba can understand the request, search standardized catalog
information, and then check participating businesses for matching
inventory.

The catalog can provide:

-   Standard names
-   Variants
-   Images
-   Product descriptions
-   Categories
-   Relationships between similar products

The business provides:

-   Availability
-   Price
-   Delivery information
-   Local promotions

This means the catalog can become an important foundation for Ntheemba
Chat E-Commerce.

------------------------------------------------------------------------

## 19. Possible Public Value in the Future

The catalog may eventually become useful beyond TradeFlow.

Possible future uses include:

-   Public product lookup
-   Barcode lookup
-   Regional product information
-   E-commerce integrations
-   POS integrations
-   Manufacturer product feeds
-   Developer APIs
-   Product discovery
-   Standardized product data for Zambia and nearby markets

The long-term opportunity is not necessarily to become the world's
largest product database.

A more realistic first goal is:

> **Become one of the most reliable structured sources of product
> information for the markets and industries Ntheemba serves.**

That alone could become a valuable platform.

------------------------------------------------------------------------

## 20. Important Design Principles

### One source of shared truth

Common product facts should be stored once and reused.

### Business freedom

Businesses can customize local names and operational information.

### IDs over names

Systems should connect products using permanent IDs, not text names.

### Variants matter

The exact sellable version of a product should have its own identity.

### Barcodes are identifiers, not the entire data model

A product can exist without a manufacturer barcode.

### Centralized media

Common images should not be uploaded separately by every business.

### Human review protects quality

Business contributions should enter a review process before becoming
trusted global data.

### Start small and grow from real use

The catalog does not need every product in Zambia on day one.

------------------------------------------------------------------------

# Roadmap and Next Steps

## Phase 1: Define the Data Model

Create the first standard schema for:

-   Business types
-   Categories
-   Manufacturers
-   Brands
-   Products
-   Variants
-   Barcodes
-   Media
-   Sources
-   Verification status

The schema should clearly separate:

1.  Global catalog data.
2.  Business-specific TradeFlow data.

------------------------------------------------------------------------

## Phase 2: Define the ID System

Create a permanent ID strategy for:

-   Categories
-   Manufacturers
-   Brands
-   Products
-   Variants

IDs should remain stable even when names change.

------------------------------------------------------------------------

## Phase 3: Create the First Seed Data

Start with a manageable amount of useful data.

Recommended first focus:

-   Retail & Grocery
-   Salon & Beauty

Do not try to collect everything immediately.

Start with:

-   Common categories
-   Major manufacturers
-   Common brands
-   Frequently sold products
-   Important variants
-   Verified barcodes where available
-   Source image URLs where available

------------------------------------------------------------------------

## Phase 4: Build the Catalog Builder

Create an internal management tool that can:

-   Import seed JSON
-   Validate records
-   Review products
-   Detect possible duplicates
-   Add and edit products
-   Manage variants
-   Manage barcodes
-   Manage media
-   Publish approved records

The Catalog Builder should become the main tool for growing and
maintaining the catalog.

------------------------------------------------------------------------

## Phase 5: Build the Media Pipeline

The media process can work like this:

**Source URL → Download → Validate → Optimize → Upload to centralized
storage → Save permanent media URL**

Possible centralized storage can include an object-storage service
designed for images and videos.

The production catalog should use the permanent centralized media
reference rather than depending on temporary external image links.

------------------------------------------------------------------------

## Phase 6: Integrate Smart Product Creation Into TradeFlow

When a business creates a product:

1.  Search the central catalog as the user types.
2.  Show matching products and variants.
3.  Let the user select the correct item.
4.  Import shared catalog information.
5.  Ask the business only for local information such as cost, price, and
    stock.
6.  Save the permanent catalog or variant ID in the business product
    record.

This should be one of the most visible benefits of the centralized
catalog.

------------------------------------------------------------------------

## Phase 7: Add Barcode Lookup

When a barcode is scanned:

1.  Search the business's local products.
2.  If not found locally, search the central catalog.
3.  If found centrally, offer to import the product.
4.  If not found, allow the business to create it.
5.  Optionally submit the new product as a catalog candidate.

------------------------------------------------------------------------

## Phase 8: Add the Contribution and Review System

Allow TradeFlow businesses to contribute missing product information.

New contributions should enter a pending review queue.

The catalog administrator can:

-   Approve
-   Correct
-   Merge
-   Reject
-   Request more information

This allows the catalog to grow through real-world usage while
protecting data quality.

------------------------------------------------------------------------

## Phase 9: Integrate Ntheemba

Connect Ntheemba to the central catalog so it can understand:

-   Product names
-   Alternative names
-   Brands
-   Categories
-   Variants
-   Sizes
-   Related products

Ntheemba can combine this shared knowledge with live business
information from TradeFlow.

------------------------------------------------------------------------

## Phase 10: Enable Chat E-Commerce

Use the catalog as the common product language between:

-   Customers
-   Ntheemba
-   TradeFlow
-   Participating businesses

This can support conversational product search and shopping without
requiring every business to independently create perfect product
descriptions and media.

------------------------------------------------------------------------

# Immediate Starting Point

The first practical milestone should be small:

1.  Finalize the first catalog schema.
2.  Create the ID rules.
3.  Choose the first Retail & Grocery categories.
4.  Choose the first Salon & Beauty categories.
5.  Create a small set of seed JSON files.
6.  Add a few major manufacturers and brands.
7.  Add common products and their variants.
8.  Verify available barcodes and source URLs.
9.  Build a simple Catalog Builder prototype.
10. Connect the catalog to TradeFlow's product creation flow.

The first version does not need thousands of products.

It only needs enough real products to prove that:

> **A business can create or import products much faster because the
> system already understands what those products are.**

------------------------------------------------------------------------

# Long-Term Vision

The centralized catalog can become a shared knowledge foundation across
the entire Ntheemba ecosystem.

**TradeFlow** manages business operations.

**The Central Catalog** understands products.

**Ntheemba** understands conversations and customer intent.

**Chat E-Commerce** connects customer demand with real business
inventory.

Together, they can create a system where product information is created
once, improved over time, and reused everywhere.

The long-term vision is simple:

> **Build one trusted product knowledge layer that makes every connected
> business faster, smarter, and easier to discover.**
