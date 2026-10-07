package listener;

import jakarta.servlet.ServletContext;
import jakarta.servlet.ServletContextEvent;
import jakarta.servlet.ServletContextListener;
import jakarta.servlet.annotation.WebListener;

import model.RoleFactory;

/**
 * Application Lifecycle Listener implementation class CreateRoleList
 *
 */
@WebListener
public class SetupApllication implements ServletContextListener {

    /**
     * Default constructor. 
     */
    public SetupApllication() {
        // TODO Auto-generated constructor stub
    }

	/**
     * @see ServletContextListener#contextInitialized(ServletContextEvent)
     */
    public void contextInitialized(ServletContextEvent sce)  { 
         // TODO Auto-generated method stub
    	ServletContext application= sce.getServletContext();
    	application.setAttribute("appRoleMap",RoleFactory.getAppRoleMap());
    }

	/**
     * @see ServletContextListener#contextDestroyed(ServletContextEvent)
     */
    public void contextDestroyed(ServletContextEvent sce)  { 
         // TODO Auto-generated method stub
    }
	
}
