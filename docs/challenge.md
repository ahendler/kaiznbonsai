## Description

- The idea of this case is for you (the candidate) to build an inventory management application. Keep in mind that your project has to be usable by Food & Beverages CPG brands.
- In this application I should be able to:
  - Register products
    - Products can be manually added
    - Products have can have stock and the stock can be added by a purchase order
    - Products can have these units:
      - kg and g
      - L and mL
      - unit
    - Each product should have at minimum: name, description, and SKU/code
  - Manage Product Stocks
    - Stocks can be manually added or added via Purchase Orders
    - Each stock has a unique identifier
  - Sell products (Product Stocks are sold)
    - Create sales orders to record product sales
    - Track quantity sold and selling price per unit
  - Track Financial Information
    - How much was sold and bought (both quantity and monetary values)
    - Profit Analysis
      - Calculate profit margins by comparing purchase costs against sales revenue
      - Display total revenue, total costs, and profit for products

## **Example Scenario**

A user purchases 100 units of Product A through a purchase order at a total cost of $100 ($1 per unit). Later, they create a sales order selling all 100 units at $10 per unit, generating $1,000 in revenue. The system should display:

- Total purchase cost: $100
- Total sales revenue: $1,000
- Profit: $900
- Profit margin: 900%

## Requisites

### Backend (Python/Django)

- Use Django + Django Rest Framework to build a RESTful API
- Postgres for database
- Design database models for:
  - Products
  - Stock
  - Purchase Orders
  - Sales Orders
  - Users
  - Or any model you judge is needed for the application to work as expected
- Implement API endpoints for all CRUD operations
- Handle profit calculations and financial tracking on the backend
- Implement authentication and authorization to ensure users only access their own data

### **Frontend (Typescript + React)**

- Use React to build a UI to visualize data and do the necessary operations
  - TanstackQuery for fetching API data
  - Use Mantine components to build the UI
  - Tailwind for styling when needed
- Create interfaces for:
  - User login/authentication
  - Product listing and creation
  - Purchase order creation and management
  - Sales order creation and management
  - Financial dashboard showing profit analysis
    - On each item, the user should be able to visualize financial information
  - Or any interface you judge is needed for the application to work as expected
- All data should be fetched from and sent to the Django API
- Deploy your application in any cloud provider that you feel confortable
  - Dockerize the application

### **Authentication**

- Simple login system with each user being able to visualize their own data only
- Users should only see products, purchase orders, and sales orders they created
- Implement proper authentication on both frontend and backend

### **Optional, but desirable**

- Create tests using pytest for the core modules of the application
  - Focus on testing business logic like profit calculations
  - Test API endpoints
  - Test model validations

### **Documentation**

- Document Architectural and Technical decisions:
  - The project should have a README file with a general overview of the project setup.
  - The candidate can build diagrams or anything that could help to understand the project and decisions.
  - API endpoints documentation.

### **Evaluation Criteria**

We will evaluate your submission based on:

- **Functionality**: Does the application meet all the business requirements ?
- **Code Quality**: Clean, maintainable, and well-organized code
- **API Design**: RESTful principles and proper structure
- **Frontend Implementation**: Effective use of React, TanstackQuery, and Mantine
- **Security**: Proper implementation of authentication and data isolation between users
- **Documentation**: Clear explanation of your decisions and how to run the project
- **Architecture**: Well-reasoned technical and architectural choices
- **UI:** A clean UI is always appreciated!

### **Timeline**

- You have **one week** from receiving this case to submit your challenge.
  - **Coding speed and quality** are valuable assets in our startup. While you have a week to complete this task, we encourage you to submit it as soon as possible.

### **Submission**

- Please share your code via a GitHub repository (or similar) and include all documentation in the repository. Send us the link when you're ready.
- If you have any questions about the requirements, feel free to reach out.
- If you haven't completed the challenge by the deadline, submit what you have and we'll check it out.

### General Comments

- We cannot monitor if you build the entire application with AI, but we want you to be able to explain technical and architectural decisions, we will ask questions about it and also evaluate the code quality.
- Don't focus exclusively on the case requirements, they should all be achieved, however you're free to have ideas and propose new solutions to the given problem. Be creative !

### References

- https://docs.djangoproject.com/en/5.2/
- https://www.django-rest-framework.org/
- https://www.cdrf.co/
- https://tanstack.com/query/latest
- https://mantine.dev/
- https://docs.pytest.org/en/stable/
