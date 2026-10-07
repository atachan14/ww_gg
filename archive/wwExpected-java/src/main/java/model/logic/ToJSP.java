package model.logic;

import java.io.Serializable;

public class ToJSP implements Serializable{
	
	
	public ToJSP() {

	}
	
	
	
	
	public String perF(float value) {
        return String.format("%.1f", value * 100);
    }


}
